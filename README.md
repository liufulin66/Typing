# 键程 Keyjourney

一个在自己电脑上运行的中英文打字练习网站。支持全文、1/3/5 分钟限时练习，以及从 F/J 开始的 16 关标准指法课程。浏览器处理即时反馈，Flask 负责内容与结算，SQLite 保存成绩。

## 在 Windows 启动

需要 Python 3.12 或更新版本。打开项目目录中的 PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m typing_app
```

在浏览器打开 **http://127.0.0.1:5000**。终端按 `Ctrl+C` 停止；以后只需执行最后一条命令即可重新启动。无需激活虚拟环境，也无需 Node、前端构建或单独的数据库服务。首次安装依赖需要联网，正常练习使用本地资源。

如果 5000 端口已被占用，可在当前 PowerShell 设置另一个端口：

```powershell
$env:PORT = '5001'
.\.venv\Scripts\python.exe -m typing_app
```

此时打开 http://127.0.0.1:5001。PyCharm 中也可以选择 `.venv\Scripts\python.exe` 为项目解释器，运行模块 `typing_app`，工作目录为项目根目录。

## 成绩存在哪里

数据库文件为 `instance/typing.sqlite3`。启动只创建缺失的表，不清空历史成绩；浏览器缓存被清理后，本地数据库仍然保留。关卡通过状态由已保存的通过成绩推导，复习失败不会回锁。

备份时先停止应用，再复制整个 `instance` 目录。恢复时同样先停止应用，再放回备份目录。不要在应用运行时直接覆盖数据库文件。`.gitignore` 已排除实例数据、虚拟环境和测试临时文件。

## 验证

后端使用 Python 标准库 `unittest`，测试数据位于项目 `.tmp/tests` 中的独立目录，不会使用个人数据库：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

OpenSpec 方案与任务位于 `openspec/changes/add-python-typing-practice/`。
本次功能和浏览器检查的具体结果见 [实施验证记录](docs/verification.md)。

## 课程数据

`typing_app/data/lessons.json` 定义 16 关，前 14 关每次新增 1 至 2 个字母，后两关为全字母和单词复习。关卡标识与课程版本用于关联通过成绩，避免用可变的页面下标保存进度。第一关默认开放，其余关卡要求全部前置关卡曾经通过；复习失败不会撤销通过记录。修改已使用课程的顺序或版本时应另行迁移，不能直接清空个人成绩。

## JSON 接口

所有接口与页面同源，字段名为 snake_case，语言为 `zh`/`en`，模式为 `full`/`timed`/`lesson`。

| 接口 | 请求与响应 |
|---|---|
| `GET /api/articles?language=zh` | 返回 `articles` 数组，每项含 `id`、`title`、`text`、`language` |
| `GET /api/lessons` | 返回 `lessons`、`next_lesson`、`completed`、`total`、`all_done` 和 `finger_map` |
| `POST /api/runs` | 接收 `mode`、`language` 与 `article_id` 或 `text`；限时还需 `duration_seconds`，关卡使用 `lesson_id`；返回 `run` |
| `POST /api/runs/<run_id>/result` | 接收 `final_input`、`attempted_chars`、`correct_attempts`、`elapsed_ms`；返回 `result` 和最新 `progress` |
| `GET /api/history?limit=20&offset=0` | 返回倒序的 `results`、总数 `total` 和汇总 `summary`；每页 1 至 100 条 |

新会话或新成绩返回 201；相同会话的相同结果重试返回 200。错误响应格式为 `{"error":"可理解的说明"}`：400 为参数或计数错误，403 为关卡锁定，404 为未知标识，409 为同一会话提交不同结果，503 为数据库暂时不可用。客户端传入的 `passed` 或速度值不会控制结算。

下面是独立的接口演示：数据库使用 `.tmp/api-example.sqlite3`，不会写入个人成绩。把代码保存为项目目录中的临时 Python 文件，并用项目解释器运行即可；也可以逐行在 Python 控制台执行。

```python
from typing_app import create_app

app = create_app({"TESTING": True, "DATABASE": ".tmp/api-example.sqlite3"})
with app.test_client() as client:
    response = client.post("/api/runs", json={
        "mode": "full", "language": "en", "text": "fj"
    })
    assert response.status_code == 201
    run = response.json["run"]
    payload = {
        "final_input": "fj", "attempted_chars": 2,
        "correct_attempts": 2, "elapsed_ms": 1000
    }
    saved = client.post(f'/api/runs/{run["id"]}/result', json=payload)
    assert saved.status_code == 201
    assert saved.json["result"]["accuracy"] == 100
    repeated = client.post(f'/api/runs/{run["id"]}/result', json=payload)
    assert repeated.status_code == 200
    history = client.get("/api/history").json
    assert history["results"][0]["run_id"] == run["id"]
    print("会话创建、成绩保存、幂等重试和历史查询均成功。")
```

### 计分定义

以 Unicode 码点计字符，空格和标点参与比对，CRLF 换行统一成 LF。准确率为正确字符尝试数除以所有已提交字符尝试数；例如 18 次正确、1 次错误、退格后补对 1 次，结果为 19/20 = 95%，错误不会被退格抹去。中文按上屏文字计分，组字过程不计错误。

速度根据最终作答中位置正确的字符数计算：中文为字符/分钟；英文和字母关卡按每 5 个字符折合 1 个词，单位 WPM。关卡完成全文且 `correct_attempts × 100 >= attempted_chars × 95` 时通过，使用原始计数而非显示的舍入百分比，不设速度门槛。

## 浏览器引擎验收

打开 `/static/checks.html` 可运行内存中的固定计分及组合事件样例。该页面不调用成绩保存接口。开发时还可用已有 Node 运行 `node tests/engine.test.mjs` 和 `node tests/input.test.mjs`，无需安装 npm 依赖；正常使用网站不需要 Node。
计时和保存协调器还可分别用 `node tests/time.test.mjs`、`node tests/save.test.mjs` 检查。四组共 18 项前端样例也都会在浏览器检查页运行。

真实中文输入法验收步骤：在 Windows 的 Edge 或 Chrome 中选择中文文章，切换到拼音输入法；输入拼音、翻页选词再确认上屏，确认组字过程不显示错误、上屏只计一次；按 Escape 取消组字，确认未增加字符尝试；在限时即将结束时保持候选词未确认，确认结算只包含已经上屏的文字。另检查练习作答区粘贴被阻止，而自定义素材区可以粘贴。

## 练习如何开始和结束

- 选好素材、点击开始后仍不计时；第一个字符输入或输入法开始组字时才开始计时。Tab、Shift 等导航和修饰键不计字符尝试。
- 全文练习和关卡在已确认输入的字符数达到目标长度时自动结算，存在错误也会结束；结束前可以退格纠正，结束后可选择再练一次。
- 限时练习提供 1、3、5 分钟。文章打完后自动循环同一素材，继续累计；切换标签页不暂停，回到页面也不会获得额外时间。
- 中文根据输入法确认上屏的文字判错，拼音与候选阶段不记字符；到时尚未确认的内容不纳入成绩。普通英文输入直接按提交字符判定。
- 只有正常完成且有字符尝试的练习进入历史。练到一半离开不保存为完成成绩；已经结算但暂未保存的结果会在本标签页中保留，以便重试。重试练习使用新的会话，重试保存仍使用原会话。
- 保存成功后才确认关卡解锁。保存失败时保留结算结果和“重试保存”按钮；同一次结果多次提交不会重复记分。

前后端计分样例共用 `typing_app/static/score-cases.json`，浏览器检查页和后端固定样例测试以同一组预期值核对上述字符、纠错和速度定义。

## 界面检查方法

在桌面和 375 像素宽的窗口中检查首页、关卡作答区及历史列表，页面不得产生整体横向溢出，虚拟键盘须保持真实行列位置。只用 Tab、Shift+Tab、Enter 遍历操作，检查可见焦点、明确的控件标签及“继续输入”恢复焦点；Tab 不应被算作练习字符。

错误字符带波浪下划线，关卡和成绩状态带文字说明，不只依赖红绿颜色。次要文字加深以提高在浅色面板上的对比度，主要操作有可见焦点。图标为页面内 SVG，字体使用系统字体；开发工具的网络面板中应没有外部字体、CDN 或图片请求。
