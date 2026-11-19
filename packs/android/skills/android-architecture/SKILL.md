---
name: Android Architecture
description: 整洁地组织 Android 应用结构：MVVM/MVI、ViewModel、StateFlow、仓库层、导航和可选的依赖注入。适用于项目超出单个界面，或用户要求可维护的结构时。
---

# Android Architecture

## 默认：MVVM，不过度设计

```text
app/
├─ data/        # repositories, network, database
├─ domain/      # optional use cases (only if they add value)
└─ ui/
   ├─ home/     # HomeViewModel + HomeScreen/Activity
   └─ detail/
```

- **UI** 观察状态并发送事件。
- **ViewModel** 持有 UI 状态并调用仓库。
- **Repository** 隐藏数据源（网络、数据库、文件）。
- 不要在 ViewModel 里放 Android `Context`。

## ViewModel + StateFlow

```kotlin
data class HomeUiState(val loading: Boolean = false, val items: List<Item> = emptyList(), val error: String? = null)

class HomeViewModel(private val repo: ItemRepository) : ViewModel() {
    private val _state = MutableStateFlow(HomeUiState())
    val state: StateFlow<HomeUiState> = _state.asStateFlow()

    fun load() = viewModelScope.launch {
        _state.update { it.copy(loading = true, error = null) }
        runCatching { repo.items() }
            .onSuccess { items -> _state.update { it.copy(loading = false, items = items) } }
            .onFailure { e -> _state.update { it.copy(loading = false, error = e.message) } }
    }
}
```

Compose 中：`collectAsStateWithLifecycle()`。Views 中：`repeatOnLifecycle`。

## 导航

- Compose：`androidx.navigation:navigation-compose`。
- Views：Navigation Component，或简单的单 Activity + Fragment。
- 路由只保留一处真相来源；传 ID，不要传整个对象。

## 依赖注入

Hilt/Koin 是可选项，会引入额外依赖。小应用在 `Application` 类里手动构造，
或用一个简单的 `ServiceLocator` 就够了，而且能离线工作。

## 规则

- 一个类，只有一个变更理由。
- 不要在 Activity/Fragment/Composable 里写业务逻辑。
- 不要用单例持有 Activity context。
- 优先使用不可变状态和显式事件。
- 添加库之前，先查离线依赖缓存（`android-deps`）。
