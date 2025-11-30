# Dataflow Pipeline Backend

Этот репозиторий содержит бэкенд-движок для выполнения графов обработки данных (Dataflow). Система поддерживает параллельное выполнение, циклы, обработку списков и типизацию данных.

## Архитектура

Проект состоит из трех основных компонентов (`src/core`):

1.  **`Node`** (Abstract Base Class):
    *   Определяет логику одного блока обработки.
    *   Описывает типы входов (`INPUT_TYPES`), выходов (`OUTPUT_TYPES`) и параметров (`PARAMETERS`).
    *   Может иметь стратегию ожидания данных (`INPUT_STRATEGY`): `"ALL"` (ждать все) или `"ANY"` (ждать любой).

2.  **`Graph`**:
    *   Хранит структуру графа (узлы и связи).
    *   Валидирует типы данных при загрузке.
    *   Загружается из JSON-формата.

3.  **`Executor`**:
    *   Движок выполнения.
    *   Использует `multiprocessing.ProcessPoolExecutor` для параллельного выполнения узлов.
    *   Работает по событийно-ориентированной модели (Data-driven): узел запускается, как только готовы его входные данные.
    *   Поддерживает callback-функцию для уведомления UI о статусе узлов (`running`, `completed`, `error`).

## Формат графа (JSON)

Для передачи графа из GUI в бэкенд используется JSON следующей структуры:

```json
{
  "nodes": [
    {
      "id": "node_1",
      "type": "LoadImage",
      "params": { "path": "C:/images/photo.jpg" }
    },
    {
      "id": "node_2",
      "type": "GaussianBlur",
      "params": { "radius": 2.5 }
    }
  ],
  "links": [
    {
      "from_node": "node_1",
      "from_output": "image",
      "to_node": "node_2",
      "to_input": "image"
    }
  ]
}
```

## API: Запуск выполнения

```python
from core.graph import Graph
from core.executor import Executor
from nodes.image_nodes import NODE_REGISTRY

# 1. Загрузка графа
graph_data = { ... } # JSON dict
graph = Graph(NODE_REGISTRY)
graph.load_from_json(graph_data)

# 2. Функция обратного вызова для UI (опционально)
def status_callback(node_id, status):
    # status: "running" | "completed" | "error"
    print(f"Node {node_id} is {status}")

# 3. Запуск
# timeout - макс. время ожидания (защита от зависания)
executor = Executor(graph, timeout=20.0) 
executor.run(status_callback=status_callback)
```

## Особенности реализации

### 1. Циклы (`LoopMerge`)
Для создания циклов используется специальный узел `LoopMerge`.
*   **Логика**:
    *   **1-я итерация**: Берет данные из входа `initial`.
    *   **N-я итерация**: Берет данные из входа `loop_back`.
    *   Узел имеет параметр `iterations` (int), ограничивающий количество проходов.
*   **Важно для GUI**:
    *   Вход `initial` должен быть подключен к источнику данных (до цикла).
    *   Вход `loop_back` подключается к концу цепочки обработки для замыкания цикла.

### 2. Обработка списков и `Any`
*   Тип `Any` совместим с любым типом данных.
*   Некоторые узлы (например, `SaveImage`, `StitchPanorama`) могут принимать `List[Image]`.
*   `CollectImages` собирает несколько входов в один список.

### 3. Многопоточность
Узлы выполняются в отдельных процессах. Это означает, что данные между узлами сериализуются (pickle).
**Важно**: Состояние узла (`self.some_var`) обновляется и возвращается из процесса в главный поток после выполнения.

## Справочник узлов (`src/nodes/image_nodes.py`)

### Ввод/Вывод
*   **`LoadImage`**: Загружает изображение с диска. `Params: path (str)`
*   **`SaveImage`**: Сохраняет изображение или список изображений. `Params: path_prefix (str)`
    *   Если на вход подан список, сохраняет файлы с индексами `_0`, `_1` и т.д.

### Обработка изображений
*   **`GaussianBlur`**: Размытие по Гауссу. `Params: radius (float)`
*   **`Grayscale`**: Преобразование в ч/б.
*   **`BlendImages`**: Смешивание двух изображений. `Params: alpha (float)`
*   **`ConvertToJPG`**: Конвертация форматов/режимов.

### Структурные / Списки
*   **`SliceImage`**: Разрезает изображение на N полос. `Output: List[Image]`
*   **`StitchPanorama`**: Склеивает список изображений вертикально. `Input: List[Image]`
*   **`CollectImages`**: Собирает 2 входа (любых типов) в список. Поддерживает рекурсивное объединение списков.

### Логика и Анализ
*   **`LoopMerge`**: Узел слияния для циклов. `Params: iterations (int)`
*   **`ImageQualityMetric`**: Вычисляет метрику (резкость/энтропия).
*   **`SelectBest`**: Выбирает лучшее из двух изображений на основе метрик качества.

