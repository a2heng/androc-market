/*
 * fixexec.c - LD_PRELOAD shim that fixes the JVM on Android/proot environments.
 *
 * Copyright (C) 2026 lidanthedev
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * PROBLEM
 * -------
 * On Android (aarch64) chroot/proot environments such as Acode, the kernel /
 * seccomp / SELinux policy denies mprotect(PROT_EXEC) with EACCES/EPERM.
 * Every JVM (java, javac, gradle, ...) needs to mark memory executable to set
 * up its JIT code cache, so it dies immediately with:
 *
 *   Error occurred during initialization of VM
 *   Failed to mark memory page as executable - check if grsecurity/PaX is enabled
 *
 * Direct mmap(PROT_READ|PROT_WRITE|PROT_EXEC, MAP_PRIVATE|MAP_ANONYMOUS) is
 * NOT blocked on these devices, only the RW -> RWX mprotect transition is.
 *
 * SOLUTION
 * --------
 * Intercept mprotect(). When a call that would ADD PROT_EXEC is denied, fall
 * back to a data-preserving remap:
 *
 *   1. mprotect(addr, len, PROT_READ|PROT_WRITE)  - make it readable
 *   2. memcpy contents to a scratch buffer
 *   3. munmap(addr, len)
 *   4. mmap(addr, len, PROT_READ|PROT_WRITE|PROT_EXEC, MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED)
 *   5. memcpy contents back
 *
 * The remap is done at the SAME address (MAP_FIXED), which is required because
 * JIT'd code contains pc-relative references. Anonymous pages are re-mapped in
 * place, so data is preserved and the region becomes executable.
 *
 * For every other program / every successful mprotect this is a zero-cost
 * passthrough (the real libc mprotect is called directly).
 *
 * Build:
 *   cc -shared -fPIC -O2 -o fixexec.so fixexec.c -ldl
 *
 * Use:
 *   LD_PRELOAD=/path/to/fixexec.so java -version
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <sys/mman.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>

static void* (*real_mmap)(void*, size_t, int, int, int, off_t);
static int (*real_mprotect)(void*, size_t, int);
static int (*real_munmap)(void*, size_t);

int mprotect(void* addr, size_t len, int prot){
    if(!real_mprotect) real_mprotect = dlsym(RTLD_NEXT, "mprotect");
    if(!real_mmap)     real_mmap     = dlsym(RTLD_NEXT, "mmap");
    if(!real_munmap)   real_munmap   = dlsym(RTLD_NEXT, "munmap");

    int r = real_mprotect(addr, len, prot);

    /* Only intervene when the caller is ADDING PROT_EXEC and the kernel
     * refused it (Android execmem restriction). */
    if(r != 0 && (prot & PROT_EXEC) && (errno == EACCES || errno == EPERM)) {
        void* save = malloc(len);
        if(!save) return r;

        /* Make the region readable so we can copy its contents. */
        if(real_mprotect(addr, len, PROT_READ|PROT_WRITE) != 0){
            free(save); return r;
        }
        memcpy(save, addr, len);

        if(real_munmap(addr, len) != 0){ free(save); return r; }

        /* Direct executable anonymous mapping is allowed on these devices. */
        void* p = real_mmap(addr, len, PROT_READ|PROT_WRITE|PROT_EXEC,
                            MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED, -1, 0);
        if(p == MAP_FAILED){ free(save); return r; }

        memcpy(addr, save, len);
        free(save);
        return 0;
    }
    return r;
}