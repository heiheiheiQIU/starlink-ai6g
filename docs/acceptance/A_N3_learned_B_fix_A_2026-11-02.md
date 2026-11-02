# A-N3 learned：B 坏 ZIP 审查修复回执

日期：2026-11-02（Asia/Shanghai）
负责人：A
B 审查提交：`69847d8fa07fe566bcf39bc1fb909bd27d7a7367`
修复提交：`d97ff5b0a9707bdbad01cac5b5d21b70d03ef7c2`
状态：**ready_for_B_reverification**

## 修复范围

B 在固定候选 `11c00374d88dbbc5138c7b2c65029317befa989c` 上发现：哈希匹配但 ZIP 容器损坏的 `weights.npz` 会从 `numpy.load` 泄漏 `zipfile.BadZipFile`，没有转成约定的 `LearnedPolicyError(code="MODEL_FORMAT")`。

本次仅做两项变更：

- `backend/policies/learned.py::_load_bundle` 将 `zipfile.BadZipFile` 和 `EOFError` 纳入 `MODEL_FORMAT` 映射。
- `tests/test_learned_policy.py` 增加真实坏 ZIP 签名和有效 NPZ 截断两条回归。

没有重训、修改权重、归一化、训练配置、seed 选择、contracts/schema 或网关接口。

## TDD 证据

修复前，两条回归均在 `np.load → zipfile.ZipFile._RealGetContents` 处泄漏 `zipfile.BadZipFile`：

```text
2 failed in 0.42s
```

加入最小异常映射后：

```text
2 passed in 0.18s
```

随后执行：

- learned + gateway 定向：`22 passed in 1.91s`。
- A-N3 + API 组合定向：`94 passed, 1 warning in 12.32s`。
- 最终组合全库：`503 passed, 1 warning in 23.52s`。

warning 仍为 Starlette 对 AnyIO 旧别名的既有弃用提示。

## 冻结身份

| 文件 | SHA-256 |
|---|---|
| `weights.npz` | `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a` |
| `normalization.json` | `5c5fd7e843817a63ed6c486ed1c2a525243a724a6573b01681e0aa53811d2449` |
| `training_summary.json` | `fc011b87f2fdeaa0c0cd74b1de7f573d352902098ea0ca83c06f182faab672a3` |
| `model_card.md` | `7574292556c2500451b326ecf0ab4e924790dc84924b2dab253d380fdfaf87d7` |
| `manifest.json` | `949370f65165437a95b5858b23103b6cac892913592d1a4b54a3d3d4d27445a8` |
| `configs/learned_policy.json` | `518c447945783600060ab6c404186f9dc2e78f107be317fa9b26b62a448fdee2` |
| `configs/policy_train.json` | `788e361c5b204c85b232be51482323e66c03442849120c3eafcec57179a7503d` |

## 请求 B 复验

请 B 在 PR #8 新候选上复跑：

1. `test_damaged_zip_is_controlled_model_format` 与截断 NPZ 回归，确认均返回 `MODEL_FORMAT`。
2. 正常冻结包、错哈希、NaN、非法 Observation 和网关异常/超时回退。
3. 模型五文件与运行/训练配置 SHA，确认冻结身份未变。

本回执只关闭坏 ZIP 容器的受控错误缺口，不扩大为 learned 已接入 Runner/API 或算法效果签收。
