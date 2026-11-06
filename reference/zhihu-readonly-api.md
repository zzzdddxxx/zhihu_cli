# 知乎只读接口分析

> 来源：`www.zhihu.com2.har`（进入主页 → 我关注 → 进入某主页）、`www.zhihu.com3.har`（刷新）、`www.zhihu.com4.har`（回答列表 + 想法列表）、`www.zhihu.com5.har`（搜索用户）
> 结论：以下只读接口均只需 `z_c0` Cookie，无需 `x-zse-96` 签名（实测 HTTP 200）。

## 一、操作场景 → 接口映射

### 进入个人主页
| 接口 | 说明 |
|---|---|
| `GET /api/v4/me?include=...` | 当前用户信息（多次，不同 include） |
| `GET /api/v4/profile/{url_token}/infinity` | 主页信息流 |

### 点击「我关注」（关注列表）★核心
| 接口 | 说明 |
|---|---|
| `GET /api/v4/members/{url_token}/followees` | 关注列表（分页） |

### 进入某个用户主页
| 接口 | 说明 |
|---|---|
| `GET /api/v4/members/{url_token}?include=...` | 用户详情 |
| `GET /api/v4/members/{url_token}/relations/mutuals` | 互相关注（共同关注） |
| `GET /api/v4/profile/{url_token}/infinity` | 该用户主页信息流 |
| `GET /api/v3/moments/{url_token}/activities` | 该用户动态 |

### 刷新
重新拉取 `profile/infinity` + `moments/activities` + `relations/mutuals`。

## 二、关键接口详情

### 1. 关注列表 `followees`

```
GET /api/v4/members/{url_token}/followees?include=...&limit=20&offset=0
```

响应结构：
```json
{
  "paging": { "is_end": false, "is_start": true, "next": "...", "previous": "...", "totals": 123 },
  "data": [
    { "id": "...", "url_token": "li-dian-jiang-77", "name": "李电匠",
      "headline": "", "gender": -1, "avatar_url": "...",
      "answer_count": 0, "follower_count": 0, "is_followed": false, "is_following": true }
  ]
}
```

- 分页：`limit`（每页条数，默认 20）+ `offset`（偏移，0 起）
- 翻页依据：`paging.is_end` / `paging.next`（完整 URL）

### 2. 用户详情 `members/{url_token}`

```
GET /api/v4/members/{url_token}?include=allow_message,is_followed,is_following,is_org,...
```

响应结构与 `/api/v4/me` 一致：`id` / `url_token` / `name` / `headline` / `gender` / `avatar_url` / `ip_info` / `vip_info` 等。

### 3. 主页信息流 `profile/{url_token}/infinity`

```
GET /api/v4/profile/{url_token}/infinity
```

> 首次调用可能返回 `{"profile_show": 0}`，内容需配合 offset 参数二次请求（待进一步抓包确认）。

### 4. 回答列表 `members/{url_token}/answers` ★核心

```
GET /api/v4/members/{url_token}/answers?sort_by=created&include=...&limit=20&offset=0
```

响应结构：
```json
{
  "paging": { "is_end": false, "totals": 5349, "next": "...", "previous": "..." },
  "data": [
    {
      "id": "2102060765519819864",          // 回答 ID
      "excerpt": "纯文本摘要...",
      "content": "<html>完整内容</html>",
      "voteup_count": 11246,                 // 点赞数
      "comment_count": 61,                   // 评论数
      "created_time": 1793950340,
      "question": { "id": "...", "title": "...", "follower_count": ... },
      "author": { "name": "...", "avatar_url_template": "..." },
      "url": "https://www.zhihu.com/answer/..."
    }
  ]
}
```

- 排序：`sort_by=created`（按时间）/ 默认（可能是热度）
- 分页：`limit` + `offset`；总数在 `paging.totals`

### 5. 想法列表 `v2/pins/{url_token}/moments` ★核心

```
GET /api/v4/v2/pins/{url_token}/moments?offset=0&limit=20&includes=...
```

响应结构：
```json
{
  "paging": { "is_end": false, "next": "...", "previous": "..." },
  "data": [
    {
      "id": "2101844680728170593",           // 想法 ID
      "type": "pin",
      "content": "想法纯文本...",
      "content_html": "<html>...</html>",
      "excerpt_title": "...",
      "like_count": 40, "comment_count": 16, "repin_count": 0,
      "favorite_count": 1, "reaction_count": 40,
      "created": 1793899811,
      "author": { "name": "...", "avatar_url_template": "..." },
      "topics": [...], "tags": [...],
      "comments": [...],                       // 前几条评论
      "url": "https://www.zhihu.com/pin/..."
    }
  ]
}
```

- 分页：`offset`（步进 20）+ `limit`；`paging.is_end` 判断是否结束

### 6. 搜索用户 `search_v3` ★核心（昵称 → url_token）

```
GET /api/v4/search_v3?t=people&q={关键词}&correction=1&offset=0&limit=20
```

响应结构：
```json
{
  "paging": { "is_end": false, "next": "..." },
  "data": [
    {
      "type": "search_result",
      "object": {
        "url_token": "xu-ze-qiu",
        "name": "<em>奥特之父</em>",        // 带高亮标签，需去标签
        "headline": "金融界门德尔松...",
        "follower_count": 209690,            // 粉丝数（区分同名用户）
        "answer_count": 5349,
        "gender": 1,
        "avatar_url": "...",
        "is_following": false, "is_followed": false
      }
    }
  ]
}
```

- `t=people` 指定搜索用户（还有 answer/content 等类型）
- `name` 带 `<em>` 高亮标签，需 `re.sub(r"<[^>]+>", "", name)` 去除
- **重名处理**：返回多个结果，用 `follower_count` 区分，通常取粉丝最多者；或展示列表让用户选择

## 三、已实现的命令

```
zhihu login / logout / status / whoami       # 账号
zhihu search <关键词> --type people [--top N] [--num N] [--offset N]
zhihu user <url_token>
zhihu answers <url_token> --offset N --num N
zhihu pins <url_token> --offset N --num N
zhihu following <url_token> --offset N --num N   # num 默认 None（拉全部）
```

- `--type`：必填，`people/content/answer/article/pin/zvideo`
- `--top N`：取前 N 个（people 下按粉丝数降序）
- `--num N`：拉取条数，程序内自动翻页；翻页间随机 sleep 0.5~1.5s 防限流

## 四、用户标识解析（search 负责转换，其余只收 url_token）

职责单一：**只有 `search` 负责「昵称 → url_token」**，其余接口的参数严格就是 url_token。

```
zhihu search 奥特之父 --type people --top 1   →  得到 xu-ze-qiu
zhihu answers xu-ze-qiu                        →  直接用 url_token
```

`search --top 1` 内部逻辑：拉取 → people 类型按 `follower_count` 降序 → 取前 1。

> 注意：`search_v3` **没有排序参数**（无 `sort`），排序是服务端默认（相关度优先）。所以要"粉丝最多"，需客户端自己按 `follower_count` 降序。
> 粉丝列表接口推测为 `GET /api/v4/members/{url_token}/followers`，与 followees 对称，待抓包确认。

## 五、include 参数与踩坑（关键）

### include 的作用

知乎接口**默认只返回基础字段**，统计字段（粉丝数/点赞数/摘要）必须用 `include` 显式指定，否则返回 `0` 或空字符串。接口能通（HTTP 200）≠ 字段完整。

### 各接口的 include 具体值

**用户详情 `members/{token}`**（参数名 `include`）：
```
allow_message,is_followed,is_following,is_org,is_blocking,employments,
answer_count,articles_count,follower_count,follower_count_text,gender,
badge[?(type=best_answerer)].topics
```

**回答列表 `members/{token}/answers`**（参数名 `include`，很长）：
```
data[*].is_normal,admin_closed_comment,...,comment_count,content,voteup_count,
...,excerpt,...;data[*].author.badge[?...].topics;data[*].author.kvip_info;
data[*].author.vip_info;data[*].question.has_publishing_draft,relationship
```

**想法列表 `v2/pins/{token}/moments`**（参数名 `includes`，注意复数）：
```
data[*].upvoted_followees,admin_closed_comment,reaction
```

**关注列表 `members/{token}/followees`**（参数名 `include`）：
```
data[*].answer_count,articles_count,gender,follower_count,follower_count_text,
is_followed,is_following,badge[?(type=best_answerer)].topics
```

### 踩坑总结

| 坑 | 现象 | 解决 |
|---|---|---|
| include 缺失 | `follower_count=0`、`excerpt=""` | 从 HAR 抠出完整 include 配成常量 |
| `include` vs `includes` | pins 接口参数名是复数 | 各接口单独确认参数名 |
| pins `content` 为空 | 内容在 `excerpt_title`（HTML） | `content or excerpt_title` 去标签兜底 |
| name 带 `<em>` | 搜索结果 `name=<em>奥特之父</em>` | `re.sub(r"<[^>]+>", "", name)` 去标签 |

> 代码里这些 include 定义为 `client.py` 的 `_USER_INCLUDE` / `_ANSWERS_INCLUDE` / `_PINS_INCLUDE` / `_FOLLOWEES_INCLUDE` 常量。
