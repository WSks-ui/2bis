# 2Bis Studio 转型方案

## 1. 背景与目标

当前 2Bis 已经具备一个 AI 生图产品的基础能力：

1. 用户注册、登录、JWT 鉴权。
2. 文生图、参考图生成、图片编辑。
3. Redis + worker 异步任务队列。
4. 体验积分、体验包、订阅额度、失败退款。
5. 生成历史、任务状态轮询。
6. 生成规格后端下发和校验。
7. API Key 管理后台和上游审计。

但从产品心智看，它仍然主要是：

```text
输入 prompt -> 等待生成 -> 查看历史
```

这类产品容易陷入“生图工具站”的同质化竞争。用户生成完一张图后，缺少继续整理、修改、组合、推演和复用素材的工作区。

本次转型目标是将 2Bis 从“AI 图片生成网站”升级为：

> **2Bis Studio：面向创作者的 AI 视觉创作工作区。**

核心转变是：

```text
从任务中心 -> 工作区中心
从单次生成 -> 持续创作
从历史列表 -> 素材画布
从参数表单 -> 工具链与关系图
从结果图库 -> 可迭代项目资产
```

### 1.1 复审结论与修订要点

按当前代码库再次复核后，Studio 转型方向成立，但第一版不能只理解成“给现有生图页加一个画布”。真正需要提前控制的是工程边界：

1. 当前前端依赖里还没有 Vue Flow，画布方案需要先做依赖接入和性能 Spike。
2. 当前历史页已有本地缩略图能力，Studio 画布必须复用缩略图，避免直接加载原图。
3. 当前任务系统有“处理中断后退款，避免重复上游扣费”的恢复策略，Studio 工具运行必须延续这个策略。
4. Studio 会引入工作区、素材、画布节点、关系和工具运行记录，必须从第一版就定义软删除、权限校验和自动保存冲突策略。
5. Phase 3 的“画布内生成”不是简单调用现有接口，它会触及 worker 成功落库、历史记录、工作区素材和画布节点之间的一致性。

因此，本方案后续章节补充了技术 Spike、数据一致性、缩略图、自动保存、权限和迁移约束，作为进入实现前的硬性检查项。

## 2. 产品定位

### 2.1 不做什么

第一阶段不直接复制 ComfyUI。

ComfyUI 的优势是节点级可控能力：用户通过节点连接模型、参数和处理步骤，构建高度可定制的生成流水线。官方文档也明确把它定义为 node-based interface and inference engine，节点是执行任务的基础模块。

2Bis 不应该第一步就进入这种高学习成本方向。原因：

1. 当前用户更可能是创作者，而不是模型工作流专家。
2. 现有后端接的是上游图片 API，不是本地模型推理引擎。
3. 真正的节点执行引擎需要处理依赖调度、缓存、参数兼容、节点市场等复杂系统。
4. 过早做硬核节点，会拖慢从“生图网站”转向“创作网站”的关键产品验证。

### 2.2 要做什么

2Bis Studio 第一阶段应该做：

```text
语义画布 + AI 工具 + 素材关系
```

它不是让用户连接底层模型节点，而是让用户连接创作素材之间的意图关系。

例如：

```text
角色设定图 --角色参考--> 新生成任务
风格样张   --风格参考--> 新生成任务
草图构图   --构图参考--> 新生成任务
旧结果图   --生成变体--> 新图片
原图       --局部编辑--> 编辑结果
```

这里的连线表达的是创作语义，不是底层执行管线。普通用户可以理解，后端也可以逐步把这些关系转换成不同的生成参数。

## 3. 核心概念

### 3.1 Workspace

Workspace 是用户的项目空间。

示例：

1. 小说封面项目。
2. 游戏角色设定。
3. 电商主图视觉。
4. 社媒海报系列。
5. 品牌风格探索。

Workspace 负责承载：

1. 画布。
2. 素材。
3. 生成任务。
4. 素材关系。
5. 项目设置。
6. 项目封面和最近编辑时间。

### 3.2 Canvas

Canvas 是 Workspace 内的可视化创作空间。

第一版不追求 Photoshop 式精细编辑，而是一个可拖拽、缩放、连线的创作画布：

1. 放置图片。
2. 放置 prompt 文本。
3. 放置备注卡片。
4. 放置生成任务卡。
5. 对素材建立关系。
6. 从选中素材调用 AI 工具。
7. 生成结果自动落回画布。

### 3.3 Asset

Asset 是工作区里的素材实体。

第一版支持：

1. 用户上传图片。
2. AI 生成图片。
3. 编辑结果图。
4. 参考图。
5. 未来可扩展到遮罩、调色板、视频、音频、3D 素材。

Asset 不等同于 CanvasItem。一个 Asset 可以被多次放到不同画布位置，CanvasItem 只是它在画布上的表现。

### 3.4 CanvasItem

CanvasItem 是画布上的元素。

第一版类型：

| 类型 | 说明 |
| --- | --- |
| `image` | 图片素材节点 |
| `prompt` | prompt 文本节点 |
| `note` | 备注节点 |
| `task` | 正在运行或已完成的生成任务节点 |
| `group` | 分组或系列框 |
| `frame` | 画布区域框，用于整理分镜、版本、系列 |

CanvasItem 需要记录位置、大小、层级、锁定状态、关联素材等信息。

### 3.5 Relation

Relation 是画布元素之间的语义连线。

第一版建议支持：

| relation_type | 中文名 | 说明 |
| --- | --- | --- |
| `style_reference` | 风格参考 | A 的风格影响 B |
| `character_reference` | 角色参考 | A 提供角色一致性 |
| `composition_reference` | 构图参考 | A 提供构图或布局 |
| `variant_of` | 变体来源 | B 是 A 的变体 |
| `edit_source` | 编辑来源 | B 是基于 A 编辑得到 |
| `mask_for` | 遮罩关系 | A 是 B 的遮罩或局部区域 |
| `note_for` | 备注说明 | A 是 B 的说明或要求 |
| `same_series` | 同一系列 | 多个素材属于同一视觉系列 |

第一版 relation 不必全部进入上游生成参数，但必须先进入数据模型。这样后续才能基于真实用户行为决定哪些关系真正影响生成。

### 3.6 Tool

Tool 是用户在画布中对素材执行的动作。

第一版工具分三类：

| 类别 | 工具 | 说明 |
| --- | --- | --- |
| 生成类 | 文生图 | 从 prompt 生成图片 |
| 生成类 | 参考图生成 | 基于 1-3 张参考图生成 |
| 生成类 | 图片编辑 | 基于 1 张原图编辑 |
| 组织类 | 连线 | 建立素材关系 |
| 组织类 | 分组 | 把素材整理成系列 |
| 组织类 | 备注 | 添加创作说明 |
| 迭代类 | 生成变体 | 基于选中结果继续探索 |
| 迭代类 | 重新编辑 | 复用原素材和参数再生成 |

第二阶段再考虑：

1. 局部重绘。
2. 扩图。
3. 高清修复。
4. 背景移除。
5. 风格迁移。
6. 角色一致性工具。
7. 批量变体。

## 4. 目标用户与核心场景

### 4.1 目标用户

第一阶段优先服务这些人：

1. 写小说、做封面、做角色设定的个人创作者。
2. 做社媒图、活动海报、电商视觉的轻设计用户。
3. 需要整理参考图、提示词、版本结果的 AI 绘图用户。
4. 有稳定风格或角色复用需求的小团队。

不优先服务：

1. 专业模型训练用户。
2. 需要本地模型和复杂节点调度的硬核 ComfyUI 用户。
3. 需要 Photoshop 级图层和像素编辑能力的设计师。

### 4.2 核心场景

#### 场景一：角色设定

用户创建“女主角设定”工作区：

1. 上传几张参考图。
2. 在画布里用连线标记“发型参考”“服装参考”“画风参考”。
3. 输入角色描述。
4. 调用参考图生成。
5. 结果自动落到参考素材右侧。
6. 用户继续选中满意结果生成变体。

#### 场景二：海报设计

用户创建“夏季活动海报”工作区：

1. 上传品牌色、产品图、过往海报。
2. 添加 prompt 节点描述活动主题。
3. 用关系线连接产品图和风格参考。
4. 生成多版海报方向。
5. 用 frame 分组“方案 A / 方案 B / 方案 C”。

#### 场景三：小说封面

用户创建“小说封面”工作区：

1. 放入角色设定图。
2. 放入世界观参考图。
3. 放入标题和氛围备注。
4. 生成封面草案。
5. 对满意版本继续编辑背景或构图。
6. 保留所有版本关系，方便回退。

## 5. 信息架构

建议新增以下页面：

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/studio` | Studio 首页 | 工作区列表、最近项目、快速创建 |
| `/studio/:workspaceId` | 工作区画布 | 主创作界面 |
| `/studio/:workspaceId/assets` | 素材库 | 可选，第一版可放在侧边栏 |
| `/history` | 历史页 | 保留，但逐步改成可导入工作区 |
| `/plans` | 计划页 | 继续承载订阅和额度 |
| `/admin/api-keys` | API Key 控制台 | 保持现有能力 |

首页 `/` 可以逐步从“生成页”改为“最近工作区 + 快速开始”。旧的生成体验可以作为：

1. 工作区内的“快速生成”工具。
2. 新用户的默认工作区。
3. `/generate` 兼容入口。

## 6. 工作区界面设计

### 6.1 布局

建议采用四区布局：

```text
┌───────────────────────────────────────────────┐
│ 顶栏：工作区名 / 保存状态 / 额度 / 导出 / 分享  │
├──────────────┬───────────────────┬────────────┤
│ 左侧素材栏   │ 中央无限画布       │ 右侧工具栏 │
│ - 上传       │ - 图片节点         │ - 检查器   │
│ - 历史导入   │ - prompt 节点       │ - AI 工具   │
│ - 最近素材   │ - note 节点         │ - 关系设置 │
│ - 分组       │ - 关系连线         │ - 任务状态 │
└──────────────┴───────────────────┴────────────┘
```

### 6.2 关键交互

1. 拖拽上传图片到画布。
2. 从历史记录拖入画布。
3. 双击空白处创建 prompt 或 note。
4. 选中图片后右侧出现可用工具。
5. 从节点连接点拖出线，松开后选择关系类型。
6. 选中多张图片后可以执行“作为参考图生成”。
7. 生成任务以 task 节点形式出现。
8. 任务完成后 task 节点转为 image 节点，或在旁边生成新 image 节点。
9. 右键节点可以复制 prompt、下载图片、生成变体、删除、移动到分组。
10. 自动保存画布布局。

### 6.3 第一版体验原则

1. 用户不需要理解模型节点。
2. 用户先理解“素材”和“关系”。
3. 连线必须有中文语义。
4. 每次 AI 操作都必须解释会消耗多少额度。
5. 结果必须回到画布，而不是只进入历史。

## 7. 技术选型

### 7.1 候选方案

#### Vue Flow

Vue Flow 提供缩放、平移、选择、拖拽、自定义节点、自定义边、控制器和小地图等能力。它天然适合做“节点 + 连线”的编辑器，也和当前 Vue 3 技术栈匹配。

优点：

1. 与当前 Vue 项目一致。
2. 节点、边、拖拽、缩放是内建能力。
3. 自定义图片节点、prompt 节点、任务节点比较直接。
4. 适合语义关系图。
5. 后续可以逐步扩展成轻量 workflow。

缺点：

1. 不适合做像素级编辑。
2. 自由画布的图层、画笔、遮罩能力较弱。
3. 大量图片节点性能需要验证。

#### Konva / vue-konva

Konva 是 2D Canvas 框架，支持图形、拖拽、事件、图层、导出和 Vue 集成。

优点：

1. 更适合自由画布和图形编辑。
2. 适合后续做裁剪、遮罩、手绘区域、局部重绘框。
3. Canvas 渲染大量元素的性能潜力更好。

缺点：

1. 关系连线、节点选择、小地图、面板交互需要自己搭。
2. 工程量比 Vue Flow 更大。
3. 第一版容易陷入“做画布基础设施”，拖慢产品验证。

#### tldraw SDK

tldraw 是成熟的 infinite canvas / whiteboard SDK，提供白板、图形、文本、箭头、协作和持久化能力。

优点：

1. 白板基础能力完整。
2. 适合快速获得成熟无限画布体验。
3. 后续协作能力有想象空间。

缺点：

1. SDK 主要面向 React。
2. 当前项目是 Vue，集成成本和技术栈割裂更高。
3. 商业授权和长期维护边界需要先确认。

### 7.2 推荐结论

第一阶段推荐：

> **以 Vue Flow 实现 Studio Canvas 的语义节点画布。**

原因：

1. 当前最重要的是“素材关系”和“创作工作区”，不是像素级编辑。
2. 用户已经明确提到“连线以添加关系”，Vue Flow 正好覆盖这个核心。
3. 项目现有前端是 Vue 3，技术栈延续性好。
4. 第一版可以最快完成可用 MVP。

中期策略：

1. Vue Flow 负责工作区主画布。
2. 后续需要遮罩、局部重绘、手绘区域时，在工具弹窗或节点详情里引入 Konva。
3. 不在第一阶段引入 tldraw，除非决定重构为 React 或需要成熟协作白板。

### 7.3 依赖接入约束

当前 `frontend/package.json` 只有 `vue`、`vue-router`、`pinia` 和 `axios`，尚未引入画布库。进入实现前需要先做一次最小依赖变更：

1. 新增 `@vue-flow/core`，并在 Studio 入口引入 Vue Flow 的基础 CSS。
2. 背景、控制器、小地图等能力优先使用 Vue Flow 官方附属包或官方导出的组件，具体包名以安装时官方文档为准，不在方案阶段写死。
3. 只在 Studio 相关页面加载画布依赖，避免影响旧生成页首屏。
4. 安装后检查 Vite 构建体积和首屏加载，确认对非 Studio 用户没有明显拖累。
5. 如果 Vue Flow 的图片节点性能或移动端交互不达标，再评估 Konva，但不要在第一版同时引入两套主画布。

### 7.4 实施前技术 Spike

在正式进入 Phase 1 前，建议先用 1-2 天做一个不可上线的 Spike，目标是验证关键风险，而不是做完整 UI。

Spike 验收项：

1. 在 `/studio-spike` 或本地临时页渲染 Vue Flow 画布。
2. 支持 100 个图片节点、50 个 prompt/note 节点、200 条关系线。
3. 节点内图片使用缩略图尺寸，不直接加载原图。
4. 支持拖拽移动、框选、缩放、小地图或视图定位。
5. 拖动结束后以 500-1000ms debounce 批量保存节点位置。
6. 模拟一个 task 节点从 `pending` 到 `success`，完成后替换或新增 image 节点。
7. 在桌面宽屏和常见笔记本尺寸下检查侧栏、画布、工具栏不会互相挤压。

如果 Spike 不能稳定通过，就先收缩 MVP：只做工作区、素材库和静态画布，不急着接入画布内生成。

## 8. 后端数据模型设计

### 8.1 新增表

#### workspaces

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `user_id` | int | 所属用户 |
| `name` | string | 工作区名称 |
| `description` | text | 描述 |
| `cover_asset_id` | int nullable | 封面素材 |
| `settings_json` | text | 工作区设置 |
| `canvas_revision` | int | 画布修订号，用于自动保存和并发控制 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `last_opened_at` | datetime nullable | 最近打开时间 |
| `archived_at` | datetime nullable | 归档时间 |
| `deleted_at` | datetime nullable | 软删除时间 |

#### workspace_assets

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `workspace_id` | int | 所属工作区 |
| `user_id` | int | 所属用户，便于权限校验 |
| `asset_type` | string | `image` / `prompt` / `note` / 后续扩展 |
| `source_type` | string | `upload` / `generated` / `edited` / `history_import` |
| `title` | string nullable | 素材标题 |
| `url` | text nullable | 图片地址 |
| `thumbnail_url` | text nullable | 缩略图 |
| `mime_type` | string nullable | 文件类型 |
| `width` | int nullable | 图片宽 |
| `height` | int nullable | 图片高 |
| `text_content` | text nullable | prompt 或 note 内容 |
| `task_id` | int nullable | 来源任务 |
| `history_id` | int nullable | 来源历史记录 |
| `parent_asset_id` | int nullable | 来源素材 |
| `metadata_json` | text | 扩展信息 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `deleted_at` | datetime nullable | 软删除时间 |

#### canvas_items

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `workspace_id` | int | 所属工作区 |
| `asset_id` | int nullable | 关联素材 |
| `task_id` | int nullable | 关联任务 |
| `item_type` | string | `image` / `prompt` / `note` / `task` / `group` / `frame` |
| `x` | float | 画布 X |
| `y` | float | 画布 Y |
| `width` | float | 宽 |
| `height` | float | 高 |
| `rotation` | float | 旋转角 |
| `z_index` | int | 层级 |
| `locked` | bool | 是否锁定 |
| `title` | string nullable | 标题 |
| `data_json` | text | 节点自定义数据 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `deleted_at` | datetime nullable | 软删除时间 |

#### canvas_relations

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `workspace_id` | int | 所属工作区 |
| `source_item_id` | int | 来源节点 |
| `target_item_id` | int | 目标节点 |
| `relation_type` | string | 关系类型 |
| `label` | string nullable | 用户自定义标签 |
| `strength` | float | 权重，默认 1 |
| `data_json` | text | 扩展信息 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `deleted_at` | datetime nullable | 软删除时间 |

#### tool_runs

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键 |
| `workspace_id` | int | 所属工作区 |
| `user_id` | int | 用户 |
| `tool_type` | string | `text2img` / `ref2img` / `edit` / `variant` |
| `status` | string | `pending` / `running` / `success` / `failed` |
| `task_id` | int nullable | 对应生成任务 |
| `idempotency_key` | string nullable | 幂等键，防止重复创建工具运行 |
| `input_item_ids_json` | text | 输入节点列表 |
| `input_asset_ids_json` | text | 输入素材列表 |
| `output_item_ids_json` | text | 输出节点列表 |
| `output_asset_ids_json` | text | 输出素材列表 |
| `options_json` | text | 工具参数 |
| `error_message` | text nullable | 失败原因 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `finished_at` | datetime nullable | 完成时间 |

### 8.2 修改现有表

建议在现有表增加可选字段：

#### generation_tasks

新增：

1. `workspace_id`
2. `canvas_item_id`
3. `tool_run_id`

#### generate_histories

新增：

1. `workspace_id`
2. `asset_id`
3. `tool_run_id`

这样旧生成链路仍可运行，Studio 内发起的生成任务可以和工作区绑定。

### 8.3 数据一致性与幂等边界

Studio 内的 AI 工具不能简单理解为“前端多传几个 workspace 字段”。它会跨越扣费、任务队列、上游图片生成、图片存储、历史记录、素材库和画布节点，必须从第一版就定义幂等边界。

建议规则：

1. `tool_runs.idempotency_key` 对同一用户、同一工作区唯一，前端重复提交时返回已有 tool run。
2. `generation_tasks.tool_run_id` 和 `tool_runs.task_id` 建议建立唯一关系，避免一个工具运行创建多个上游任务。
3. Studio 输出素材应通过 `task_id` 或 `tool_run_id` 做唯一约束，worker 重试本地落库时不能重复创建多张相同 asset。
4. worker 收到上游图片结果后，后续本地落库失败不能再次请求上游；应进入“本地收尾待修复”路径，按 `task_id` 重试创建 history、asset、canvas item 和 relation。
5. 成功收尾时，`generation_tasks`、`generate_histories`、`tool_runs`、`workspace_assets`、`canvas_items`、`canvas_relations` 尽量在同一个数据库事务中写入。
6. 如果远程图片后续被 `mirror_remote_image` 镜像成本地地址，Studio 的 `workspace_assets.url` 和 `thumbnail_url` 也需要同步更新，不能只更新 task 和 history。

当前 worker 已经有处理中断恢复逻辑：对长时间卡在 `processing` 的任务退款，避免重复上游计费。Studio 工具运行必须沿用这个原则。凡是可能已经打到上游的失败，都要优先防止重复请求上游，再考虑本地补偿修复。

### 8.4 软删除与归档

Studio 不建议第一版做硬删除。

原因：

1. 同一张 asset 可能被多个 canvas item 使用。
2. 历史记录、任务、素材、画布节点之间会互相引用。
3. 本地文件和未来 S3 文件的删除成本不同，误删后恢复困难。
4. 用户在创作工作区里经常需要“移出画布”，不等于“永久删除素材”。

建议策略：

1. workspace 删除先写 `archived_at` 或 `deleted_at`。
2. asset 删除先写 `deleted_at`，默认不删源文件。
3. canvas item 删除先写 `deleted_at`，并软删除相关 relation。
4. history 导入到 Studio 后，删除 history 不应立即删除已被 asset 引用的文件。
5. 真正的文件清理单独做后台 cleanup job，按引用计数或明确的孤儿文件规则执行。

### 8.5 缩略图策略

当前项目已经有 `image_derivatives.ensure_thumbnail(image_url)`，历史页列表会为本地 `/static/images/...` 图片生成 WebP 缩略图。Studio 应直接复用这条能力，但要注意它当前只处理本地静态图片：远程 URL 或 S3 公网 URL 会直接返回原图 URL。

第一版建议：

1. `workspace_assets.thumbnail_url` 入库保存，画布节点优先加载 `thumbnail_url`。
2. 上传素材、历史导入、worker 生成结果落入 Studio 时都调用缩略图生成。
3. 对远程 URL 或 S3 URL，第一版可以暂时回退到原图 URL，但要在性能验收里标记风险。
4. 如果 S3 是正式部署路径，应补一个远程缩略图生成流程：下载到临时文件生成 WebP，再上传到 S3 或本地静态目录。
5. 画布中只加载缩略图，大图只在预览弹窗、下载或编辑器里加载。

### 8.6 自动保存与并发控制

画布自动保存不能直接在每次拖动时请求接口。

第一版建议：

1. 前端拖动中只更新本地状态，拖动结束后触发保存。
2. 批量保存接口使用 500-1000ms debounce，并合并连续位置变更。
3. `workspaces.canvas_revision` 或 `updated_at` 作为乐观并发字段。
4. 保存请求带 `client_revision`，后端成功后返回新的 `server_revision`。
5. 第一版可接受单用户、单标签页的 last-write-wins，但必须在方案中明确“不保证多标签页并发编辑安全”。
6. 如果服务端发现 revision 落后，返回 409，让前端提示重新加载或执行一次轻量合并。

### 8.7 权限与安全约束

所有 Studio API 都必须以当前登录用户为边界，不能只依赖前端传入的 workspace id。

必须校验：

1. 查询、修改、删除 workspace 时必须带 `workspaces.user_id == current_user.id`。
2. 创建 asset 时，目标 workspace 必须属于当前用户。
3. 导入 history 时，history 必须属于当前用户。
4. 创建 canvas item 时，关联 asset 和 task 必须属于同一用户和同一 workspace。
5. 创建 relation 时，source item、target item 必须属于同一 workspace 和同一用户。
6. Studio tool API 选择的输入 item / asset 必须全部属于当前 workspace。
7. 管理员 API Key 后台不应暴露 Studio workspace 数据，除非后续明确做运营审计页。

### 8.8 迁移与本地 SQLite 兼容

当前项目既有 Alembic 迁移，也在 `database.py` 里对 SQLite 做启动时补丁，补齐旧本地库缺失字段。Studio 新表和新字段需要同时考虑这两条路径。

建议：

1. 正式数据库变更走 Alembic migration。
2. 本地 SQLite 开发库需要在 `database.py` 的 SQLite 兼容逻辑中补齐新增表或关键字段。
3. 新增 enum 或状态值时，优先用字符串字段，避免 SQLite 和异步迁移环境里 enum 维护成本过高。
4. 大批量新增表时，先保证空库 `Base.metadata.create_all` 可用，再验证旧库启动补丁可用。
5. 测试里至少覆盖一次“旧库无 Studio 表，启动后可创建工作区”的路径。

## 9. 后端 API 设计

### 9.1 Workspace API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/workspaces` | 获取当前用户工作区列表 |
| `POST` | `/api/workspaces` | 创建工作区 |
| `GET` | `/api/workspaces/{id}` | 获取工作区详情 |
| `PATCH` | `/api/workspaces/{id}` | 更新名称、描述、封面 |
| `DELETE` | `/api/workspaces/{id}` | 删除或归档工作区 |

### 9.2 Canvas API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/workspaces/{id}/canvas` | 获取画布 items 和 relations |
| `POST` | `/api/workspaces/{id}/canvas/items` | 创建单个节点 |
| `PATCH` | `/api/workspaces/{id}/canvas/items/{item_id}` | 更新节点位置、大小、数据 |
| `POST` | `/api/workspaces/{id}/canvas/items/bulk` | 批量保存节点布局，携带 `client_revision` |
| `DELETE` | `/api/workspaces/{id}/canvas/items/{item_id}` | 删除节点 |
| `POST` | `/api/workspaces/{id}/canvas/relations` | 创建连线关系 |
| `PATCH` | `/api/workspaces/{id}/canvas/relations/{relation_id}` | 修改关系类型或标签 |
| `DELETE` | `/api/workspaces/{id}/canvas/relations/{relation_id}` | 删除关系 |

`GET /canvas` 建议返回：

1. `workspace` 基本信息。
2. `revision` 当前画布修订号。
3. `items` 未删除节点。
4. `relations` 未删除关系。
5. `assets` 当前画布会用到的素材简表，至少包含 `id`、`url`、`thumbnail_url`、`width`、`height`。

批量保存接口建议只保存布局类变更：`x`、`y`、`width`、`height`、`z_index`、`locked`、`data_json` 中的 UI 状态。新增素材、创建关系、执行工具仍走独立 API，便于权限校验和审计。

### 9.3 Asset API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/workspaces/{id}/assets` | 获取工作区素材 |
| `POST` | `/api/workspaces/{id}/assets/upload` | 上传图片素材 |
| `POST` | `/api/workspaces/{id}/assets/import-history` | 从历史记录导入素材 |
| `PATCH` | `/api/workspaces/{id}/assets/{asset_id}` | 更新素材标题或元数据 |
| `DELETE` | `/api/workspaces/{id}/assets/{asset_id}` | 删除素材 |

素材删除默认软删除。接口返回时应过滤 `deleted_at is null` 的素材；如果素材仍被画布节点引用，删除动作应先提示用户“从素材库隐藏”还是“同时从画布移除”。

### 9.4 Tool API

第一版可以不完全新建生成系统，而是 Studio API 包装现有生成能力。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/workspaces/{id}/tools/text2img` | 在工作区内创建文生图任务 |
| `POST` | `/api/workspaces/{id}/tools/ref2img` | 基于选中素材创建参考图任务 |
| `POST` | `/api/workspaces/{id}/tools/edit` | 基于选中素材创建编辑任务 |
| `POST` | `/api/workspaces/{id}/tools/variant` | 基于选中结果创建变体任务 |
| `GET` | `/api/workspaces/{id}/tool-runs/{run_id}` | 查询工具执行状态 |

内部仍然复用：

1. `GenerationOptions`
2. `QuotaManager`
3. `enqueue_generation_task`
4. `AIClient`
5. `image_storage`

工具创建接口建议接受 `idempotency_key`、`input_item_ids`、`input_asset_ids`、`output_position` 和完整生成参数。后端负责把这些信息固化到 `tool_runs.options_json`，并创建对应 `generation_tasks`。前端不应该直接推断最终 asset id 或 canvas item id。

## 10. 前端模块设计

### 10.1 新增页面

1. `frontend/src/views/Studio.vue`
2. `frontend/src/views/StudioWorkspace.vue`

### 10.2 新增组件

建议新建目录：

```text
frontend/src/components/studio/
├── StudioCanvas.vue
├── StudioTopBar.vue
├── StudioAssetPanel.vue
├── StudioToolPanel.vue
├── StudioInspector.vue
├── StudioTaskQueue.vue
├── nodes/
│   ├── ImageNode.vue
│   ├── PromptNode.vue
│   ├── NoteNode.vue
│   ├── TaskNode.vue
│   └── GroupNode.vue
├── edges/
│   └── RelationEdge.vue
└── menus/
    ├── RelationTypeMenu.vue
    └── NodeContextMenu.vue
```

### 10.3 新增 Store

```text
frontend/src/stores/workspaces.js
frontend/src/stores/canvas.js
frontend/src/stores/assets.js
```

职责：

1. `workspaces.js` 管理工作区列表和当前工作区。
2. `canvas.js` 管理 nodes、edges、选中状态、自动保存。
3. `assets.js` 管理素材上传、历史导入、素材列表。

现有 `tasks.js` 可以继续负责生成任务轮询，但需要支持 workspace 场景：

1. 任务完成后通知 canvas store。
2. 生成结果创建 asset。
3. 生成结果创建 canvas item。
4. 自动创建 relation。

### 10.4 前端状态与保存策略

Studio 前端要把“画布交互状态”和“服务端持久化状态”分开管理。

建议：

1. `canvas.js` 保存 Vue Flow nodes / edges、选中状态、viewport、`serverRevision`、`dirty`、`saving`、`saveError`。
2. 拖动节点时只更新本地 nodes；拖动结束后把变更加入 pending patch 队列。
3. 自动保存只发送变化过的节点，不全量提交整张画布。
4. 保存成功后更新 `serverRevision` 和节点的 `updated_at`。
5. 保存失败时在顶栏显示“未保存”，不要静默丢失用户移动。
6. 收到 task 成功轮询结果后，重新拉取对应 tool run 或增量拉取 canvas，避免前端自己拼装最终节点导致和后端不一致。
7. 图片节点组件只渲染 `thumbnail_url`；预览弹窗才加载 `url`。

### 10.5 UI 边界

第一版 Studio 是工作工具，不是营销页。

界面原则：

1. 默认进入真实工作区列表或最近工作区，不做大 Hero。
2. 顶栏、侧栏、工具栏保持紧凑，优先留空间给画布。
3. 工具按钮使用图标和短标签，例如上传、连线、生成、备注、分组。
4. 右侧 inspector 展示当前选中节点可执行的操作，不在画布中放大量说明文字。
5. 空工作区可以给一个简短空状态，但应直接提供“上传图片”“添加 Prompt”“从历史导入”三个入口。

## 11. 与现有功能的迁移关系

### 11.1 首页

短期：

1. 保留当前首页生成体验。
2. 新增导航入口“Studio”。
3. 首页生成任务仍进入历史。

中期：

1. 首页变成最近工作区和快速创建。
2. 旧生成表单进入 `/generate` 或工作区内工具。

### 11.2 历史记录

历史页不删除，增加“导入到工作区”。

导入后：

1. 创建 workspace_asset。
2. 创建 canvas_item。
3. 保留 history 与 asset 的关联。

### 11.3 任务系统

现有任务系统继续作为底层。

Studio 只是给任务增加上下文：

1. 属于哪个 workspace。
2. 来源于哪些 canvas items。
3. 完成后结果放到哪个位置。
4. 自动建立哪些 relation。

### 11.4 计费系统

不新增新的账务模型。

所有 AI 工具仍然走：

1. `QuotaManager.deduct_for_generation`
2. `balance_source`
3. worker 失败退款

画布组织操作不扣费：

1. 移动节点。
2. 连线。
3. 添加 note。
4. 分组。
5. 改名。

AI 生成、编辑、变体、未来高清修复等工具才扣费。

## 12. 分阶段实施计划

### Phase 0: 产品边界冻结

目标：先明确第一版范围，避免做成无限大白板或 ComfyUI 复刻。

任务：

1. 确定产品名：`2Bis Studio`。
2. 确定第一版只做语义画布，不做底层模型节点。
3. 确定第一版使用 Vue Flow。
4. 确定第一版 relation 类型。
5. 确定不做实时协作。
6. 确定不做像素级图层编辑。
7. 完成 Vue Flow Spike，验证依赖接入、100 节点性能、自动保存和 task 节点状态变化。

验收标准：

1. 方案冻结。
2. UI 原型或低保真线框完成。
3. 数据模型字段确认。
4. Spike 结论明确：继续 Vue Flow、收缩范围，或切换方案。

### Phase 1: 工作区与静态画布

目标：用户可以创建工作区，并在画布上摆放素材和备注。

后端任务：

1. 新增 workspace 表。
2. 新增 workspace_assets 表。
3. 新增 canvas_items 表。
4. 新增基础 CRUD API。
5. 上传素材复用现有上传校验。
6. 接入本地缩略图生成，并为 asset 写入 `thumbnail_url`。
7. 实现 `canvas_revision` 和批量布局保存。

前端任务：

1. 新增 `/studio` 工作区列表。
2. 新增 `/studio/:id` 画布页。
3. 接入 Vue Flow。
4. 支持图片节点、prompt 节点、note 节点。
5. 支持拖拽移动和自动保存位置。
6. 支持保存失败提示和手动重试。

验收标准：

1. 用户可创建工作区。
2. 用户可上传图片到画布。
3. 用户可创建 prompt / note。
4. 刷新页面后布局保持。
5. 图片节点使用缩略图加载。
6. 单标签页内自动保存不会丢失最后一次拖动。

### Phase 2: 语义连线

目标：用户可以在素材之间建立创作关系。

后端任务：

1. 新增 canvas_relations 表。
2. 新增 relation CRUD API。
3. 校验 source / target 必须属于同一 workspace。

前端任务：

1. 支持节点之间拖线。
2. 连线后弹出关系类型选择。
3. 不同关系类型使用不同颜色或标签。
4. 右侧 inspector 显示关系说明。

验收标准：

1. 可以创建、修改、删除关系。
2. 关系随画布一起保存和恢复。
3. 用户能看懂每条线代表什么。

### Phase 3: 画布内生成

目标：现有 AI 生成能力进入 Studio。

后端任务：

1. 新增 workspace tool API。
2. 给 generation_tasks 增加 `workspace_id`、`canvas_item_id`、`tool_run_id`。
3. 新增 tool_runs 表。
4. worker 完成任务后创建 workspace_asset 和 canvas_item。
5. 自动建立 `variant_of`、`edit_source` 或参考关系。
6. 增加本地收尾幂等逻辑，避免上游已成功后重复请求上游。
7. 扩展远程图片镜像逻辑，同步更新 Studio asset。

前端任务：

1. 选中节点后显示可用工具。
2. 从 prompt 节点执行文生图。
3. 从 1-3 张图片节点执行参考图生成。
4. 从单张图片节点执行编辑。
5. 任务节点显示进度。
6. 结果节点自动落在来源节点右侧。

验收标准：

1. 工作区内可以完成一次文生图。
2. 工作区内可以完成一次参考图生成。
3. 工作区内可以完成一次图片编辑。
4. 失败退款仍然正确。
5. 结果进入画布和素材库。
6. worker 重启或本地落库失败后，不会重复生成同一个上游任务。

### Phase 4: 素材库和历史导入

目标：把现有历史记录转化为可复用资产。

任务：

1. 历史页增加“导入到工作区”。
2. 工作区左侧素材栏展示当前素材。
3. 支持从素材栏拖入画布。
4. 支持设置工作区封面。
5. 支持按来源、类型、时间筛选素材。

验收标准：

1. 旧历史不浪费，可以进入 Studio。
2. 画布不是唯一入口，素材库也能管理项目资产。

### Phase 5: 创作增强工具

目标：让 Studio 真正超过“画布版生图”。

建议优先级：

1. 生成变体。
2. 复用上次参数重新生成。
3. 多结果对比。
4. 局部编辑入口。
5. 扩图。
6. 高清修复。
7. 背景移除。

每个工具必须满足：

1. 有输入素材。
2. 有明确扣费。
3. 有工具运行记录。
4. 有输出素材。
5. 自动建立来源关系。

### Phase 6: 高级能力

后续再考虑：

1. 实时协作。
2. 分享只读工作区。
3. 工作区模板。
4. 项目导出。
5. 团队空间。
6. 更接近 ComfyUI 的高级 workflow 模式。

## 13. MVP 范围

第一版 MVP 建议拆成两个可验收层级，避免一开始就把画布、素材、关系和 worker 改造全部绑在同一次上线里。

### 13.1 Studio Canvas MVP

这一层优先证明“2Bis 可以从生图网站变成创作工作区”：

1. 工作区列表。
2. 单工作区画布。
3. 图片节点。
4. prompt 节点。
5. note 节点。
6. 语义连线。
7. 上传图片。
8. 历史记录导入到工作区。
9. 自动保存布局。
10. 缩略图加载。

### 13.2 Studio Generation MVP

这一层在 Canvas MVP 稳定后接入：

1. 从画布发起文生图。
2. 从画布发起参考图生成。
3. 生成任务以 task 节点显示。
4. 生成结果自动回到画布。
5. 自动建立来源关系。
6. 失败退款和本地收尾幂等验证通过。

明确不包含：

1. 实时协作。
2. ComfyUI 式模型节点。
3. 多图层像素编辑。
4. 复杂遮罩编辑。
5. 视频。
6. 公开社区。
7. 团队权限。

## 14. 关键验收标准

产品验收：

1. 用户进入 Studio 后，第一眼能理解这是“项目工作区”，不是普通生图表单。
2. 用户能把至少 3 张素材放进画布。
3. 用户能用连线表达素材关系。
4. 用户能基于画布素材发起生成。
5. 生成结果会回到画布，并保留来源关系。

技术验收：

1. 刷新后画布布局不丢。
2. 节点和关系有用户权限隔离。
3. 上传文件仍复用现有 MIME 校验。
4. 生成扣费仍走 QuotaManager。
5. worker 失败退款仍正确。
6. 老的生成入口不被破坏。

性能验收：

1. 单画布 100 个节点内操作流畅。
2. 单画布 200 条关系内可接受。
3. 自动保存不会频繁打爆接口。
4. 图片使用缩略图，避免画布加载原图。

## 15. 风险与应对

### 风险一：范围膨胀

问题：画布、白板、节点、图片编辑都可以无限扩展。

应对：

1. 第一版只做语义节点画布。
2. 不做图层系统。
3. 不做协作。
4. 不做模型节点执行引擎。

### 风险二：用户以为连线会强影响生成，但第一版只是组织关系

问题：如果关系没有进入生成参数，用户可能觉得连线只是装饰。

应对：

1. 第一版至少让 `style_reference`、`character_reference`、`composition_reference` 影响工具表单。
2. 执行参考图生成时，自动把相关 image item 作为参考图候选。
3. 在 UI 文案中说明“关系会帮助 Studio 推荐工具输入”。

### 风险三：画布性能

问题：图片节点多以后卡顿。

应对：

1. 使用缩略图。
2. 限制第一版单工作区画布节点数量提示。
3. 大图只在预览弹窗加载。
4. 保存节点布局时做 debounce。

### 风险三补充：缩略图覆盖不完整

问题：现有缩略图逻辑只稳定覆盖本地 `/static/images/...` 图片，S3 或远程图片可能仍加载原图。

应对：

1. Phase 1 先确保本地上传和本地生成结果有缩略图。
2. 如果生产使用 S3，补远程缩略图生成和上传流程。
3. 性能测试必须分别覆盖本地图片和远程图片。

### 风险四：数据模型过早复杂

问题：Workspace、Asset、Item、Relation、ToolRun 都引入后，开发量明显增加。

应对：

1. 字段保留 `data_json` 扩展。
2. 第一版只实现必要字段。
3. 不提前做团队、多画布、权限分层。

### 风险五：技术选型后悔

问题：Vue Flow 后续可能不适合自由画布和局部编辑。

应对：

1. 主画布只承载语义节点。
2. 像素编辑类能力通过工具弹窗或独立编辑器实现。
3. 后续可在局部编辑器中引入 Konva，不影响主画布模型。

### 风险六：上游成功后本地收尾失败

问题：上游已经生成图片，但本地创建 history、asset、canvas item 或 relation 失败。如果直接按普通失败重试，会重复请求上游并造成重复扣费或重复图片。

应对：

1. 把“上游请求”和“本地收尾”拆成两个可观测阶段。
2. 上游成功后记录 `image_url` 和上游审计字段，再执行本地收尾。
3. 本地收尾失败时只重试本地数据库和缩略图逻辑，不再次调用上游。
4. 用 `task_id`、`tool_run_id` 的唯一关系保证重复收尾不会创建重复 asset。

### 风险七：自动保存覆盖用户改动

问题：多标签页或弱网环境下，较旧的保存请求可能覆盖较新的画布布局。

应对：

1. 所有批量保存携带 `client_revision`。
2. 服务端返回新的 `server_revision`。
3. 版本冲突时返回 409，前端提示刷新或重试。
4. 第一版明确不做多人实时协作，避免给用户错误预期。

## 16. 测试计划

### 16.1 后端测试

覆盖：

1. 创建工作区。
2. 用户只能访问自己的工作区。
3. 上传素材并创建 asset。
4. 创建 canvas item。
5. 批量更新 item 位置。
6. 创建 relation 时校验同工作区。
7. 删除 item 时处理 relation。
8. Studio 内创建生成任务仍正确扣费。
9. worker 完成后创建 asset 和 canvas item。
10. worker 失败后仍按原逻辑退款。
11. 导入历史时校验 history 属于当前用户。
12. asset、item、relation 删除走软删除，不误删仍被引用的文件。
13. 批量保存 revision 冲突时返回 409。
14. 同一个 `idempotency_key` 重复提交时不会重复创建任务。
15. worker 本地收尾重试不会重复创建 asset 和 canvas item。
16. S3 或远程 URL 场景下缩略图回退行为符合预期。

### 16.2 前端测试

覆盖：

1. 工作区列表加载。
2. 画布 nodes / edges 渲染。
3. 拖动节点后保存。
4. 创建关系。
5. 删除关系。
6. 上传图片后出现节点。
7. 选中节点后右侧工具可用。
8. 任务完成后画布新增结果节点。
9. 保存中、保存成功、保存失败三种顶栏状态。
10. revision 冲突时提示用户重新加载或重试。
11. 图片节点使用 `thumbnail_url`，预览才使用原图 `url`。
12. 100 个图片节点和 200 条关系线的交互性能。

### 16.3 手动验收脚本

建议第一版手测流程：

1. 新建“小说封面”工作区。
2. 上传 2 张参考图。
3. 创建一个 prompt 节点。
4. 给参考图和 prompt 连线，选择“风格参考”和“角色参考”。
5. 选中 prompt 和参考图，执行参考图生成。
6. 等待任务完成。
7. 检查结果是否出现在画布。
8. 检查结果和来源是否自动连线。
9. 刷新页面确认画布恢复。
10. 检查余额扣费和失败退款。
11. 删除一个画布节点，确认素材库素材仍可保留。
12. 从历史导入一张旧图，确认不会影响原历史记录。
13. 快速连续拖动多个节点，确认最终位置保存的是最后一次拖动。
14. 模拟 worker 重启，确认不会重复请求上游生成。

## 17. 与当前开发方向的关系

当前 README 中的短期目标是稳定“体验积分 + 订阅额度”的账务闭环，并扩展专业工作流和更多生成规格。

Studio 转型并不推翻这个方向，而是把这些能力放进更强的产品容器里：

1. `QuotaManager` 继续作为所有 AI 工具的扣费核心。
2. `GenerationOptions` 继续作为生成规格权威来源。
3. `workflow_type`、`workflow_cost`、`workflow_preset` 可以从“表单字段”升级为“工具运行上下文”。
4. 历史记录从结果列表升级为可导入资产。
5. API Key 控制台继续保证上游稳定性。

换句话说，Studio 是产品层升级，不是对底层能力的否定。

## 18. 最终结论

2Bis Studio 的正确切入点不是“做一个更复杂的生图表单”，也不是“复刻 ComfyUI”。

更适合当前项目的方向是：

```text
用工作区承载项目
用画布组织素材
用语义连线表达创作关系
用 AI 工具持续生成和修改
用现有账务与任务系统保证闭环
```

推荐第一阶段采用 Vue Flow 实现“语义节点画布”，快速做出可用的创作工作区 MVP。等用户真正开始在画布中组织素材、建立关系、持续迭代后，再决定是否引入更强的像素编辑、协作、模板或高级 workflow。

## 19. 参考资料

1. Vue Flow：`https://vueflow.dev/`
2. Vue Flow 自定义节点与拖拽：`https://vueflow.dev/examples/nodes/`
3. Konva / vue-konva：`https://konvajs.org/docs/vue/index.html`
4. tldraw SDK：`https://tldraw.dev/`
5. ComfyUI 官方文档：`https://docs.comfy.org/`
6. Comfy 官方站点：`https://comfy.org/`
