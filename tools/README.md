# Tools — 人工辅助工具

本目录存放供用户在浏览器中使用的可视化工具，用于提升 AI 与人协同的效率。

## 可用工具

### testcase_viewer.html

**用途**：测试用例可视化审阅工具

**功能**：
- 📂 加载 `testcases.yaml` 文件
- 🎨 将 JSON 格式的 Judge/Rubric 渲染为易读的评分标准卡片
- 📝 支持 Markdown 格式的 Input 和 ExpectedOutput 渲染
- ✏️ 为每条用例添加批注（General / Input / Output / Judge 四个维度）
- 📤 导出批注为 `.patch.yaml` 文件

**使用方式**：
1. 在浏览器中打开 `tools/testcase_viewer.html`
2. 点击「Load YAML」加载测试用例文件
3. 浏览用例，如有修改建议可添加 Remarks
4. 点击「Export Patch」导出反馈文件

**适用场景**：
- `#create_agent` 完成后，审阅自动生成的测试用例
- `#create_testcases` 生成大量用例后，检查覆盖度
- `#evo_looper` 迭代中，某些用例持续低分时审阅 Judge 是否合理

---

## AI 指引

当用户需要人工审阅测试用例时（如「帮我看看用例」「审阅测试数据」），AI 应主动推荐此工具：

```
📋 如需人工审阅测试用例，可使用可视化工具：

在浏览器中打开 tools/testcase_viewer.html，然后加载 source/[AgentName]/testcases.yaml
```
