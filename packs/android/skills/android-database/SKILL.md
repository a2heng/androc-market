---
name: Android Database
description: 在 Android 上用 Room、SQLite 或 DataStore 存储数据，涵盖 schema、迁移、线程与测试。应用需要持久化时使用。
---

# Android 数据库

## 选型

- **DataStore（Preferences/Proto）**：小型键值配置，无需 schema。
- **Room**：关系型数据、查询、迁移、Flow 支持。
- **原生 SQLite**：只用于极小场景或既有代码；Room 更安全。

## Room 配置

```groovy
implementation 'androidx.room:room-runtime:2.6.1'
annotationProcessor 'androidx.room:room-compiler:2.6.1'
// Kotlin: use ksp/kapt matching the Kotlin plugin
```

```kotlin
@Entity data class Note(@PrimaryKey(autoGenerate = true) val id: Long = 0, val text: String)

@Dao interface NoteDao {
    @Query("SELECT * FROM Note ORDER BY id DESC") fun all(): Flow<List<Note>>
    @Insert suspend fun insert(note: Note): Long
    @Delete suspend fun delete(note: Note)
}

@Database(entities = [Note::class], version = 1)
abstract class AppDb : RoomDatabase() {
    abstract fun notes(): NoteDao
}
```

## 规则

- 绝不在主线程访问数据库。
- 使用 `suspend`/`Flow`；Room 对查询会强制这一点。
- 每次 schema 变更都需要迁移，或仅对 debug 构建使用
  `fallbackToDestructiveMigration`。
- 导出 schema（`room.schemaLocation`），让迁移可被评审。
- 用内存数据库测试（`Room.inMemoryDatabaseBuilder`）。
- 备份/恢复由应用自己负责；持有令牌的应用可以禁用 `allowBackup`。

## 检查依赖

Room 的构建产物可能不在离线缓存中。用一次小构建检查；如果缺失，
在启用 `OC_BUILD_ONLINE=1` 之前先询问。

## 在设备上调试

```sh
adb shell run-as com.example.app ls databases
adb shell run-as com.example.app sqlite3 databases/app.db '.tables'
```

正常使用 adb 即可；`auto` 会把整条命令（含变量）送进 proot。

设备上可能没有 `sqlite3`；不要依赖它来支撑应用。
