# NaiShi

面向人工智能科研的离线英语学习应用，重点覆盖时空序列预测、混合神经网络和概率模型。

## 功能

- 1900 个词条：释义、音标、搜索、收藏与会／不会标记。
- 间隔复习，英译中、中译英和拼写训练，错词重练。
- 学习记录、训练正确率及待复习数量。
- 365 句论文翻译练习、参考译文及本机草稿与历史。
- 黑白界面，Android 8.0 及以上。

## 安装与预览

在 [Releases](https://github.com/FuInSure/NaiShi/releases) 下载 APK。旧版用户直接覆盖安装，不要先卸载。打开 `词库/打开词库.html` 可使用独立网页版本。网页和安卓应用的本机数据互不自动迁移，卸载或清除数据会丢失记录。

## 内容状态

全部词条有音标，其中 319 条含未独立核验的编辑补充；短语采用分词参考读音。340 句论文参考译文和阅读提示待人工审校。词卡不提供双语教学例句。数据覆盖不等于全部内容通过专家复核。

## 构建

需要 Windows、Python 3、Pillow、JDK，以及 Android API 35 SDK 和对应 Build Tools。

```powershell
python -m pip install Pillow
$env:JAVA_HOME = '你的JDK目录'
$env:ANDROID_BUILD_TOOLS = '你的Android构建工具目录'
$env:ANDROID_JAR = '你的API35目录/android.jar'
python scripts/build_apk.py
```

安装包生成到 `dist/`。首次本地构建会创建自己的私有签名，不能覆盖安装原作者签名的版本。`.private/` 不入库，务必自行备份；后续升级保持签名与包名并递增版本号。

数据重建：依次执行 `python 词库/tools/build.py`、`python 词库/tools/finalize.py`、`python 词库/tools/render_reader.py`、`python 词库/tools/validate.py`。仅修改界面时执行后两步。

## 来源与许可

- 扩展术语改编自 [机器之心 AITD](https://github.com/jiqizhixin/Artificial-Intelligence-Terminology-Database)，遵循 CC BY-NC-SA 4.0，原许可保留在 `词库/source/LICENSE`。
- 音标采用 [IPA Dictionary](https://github.com/open-dict-data/ipa-dict) / CMUdict 与编辑补充，许可及说明在 `词库/source/pronunciation/`，并内置于界面。
- 论文短引文标注原始来源，版权归原权利人。
- 上游资料受各自许可约束；公开源码不代表所有内容可自由商用。未为项目原创代码另行授予开源许可。

已验证数据一致性、浏览器交互、APK 签名和包内资源；尚未完成安卓真机安装与性能验收。
