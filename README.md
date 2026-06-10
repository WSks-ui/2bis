# 2Bis AI Image Generator

2Bis is a full-stack AI image generation platform with text-to-image, reference-image generation, and image editing flows. Users sign in, receive daily experience points, buy a trial pack, or subscribe for monthly quota.

## Features

- JWT registration and login.
- Daily check-in rewards as experience points, valid for 10 days.
- Trial pack and subscription quota billing.
- Async generation tasks backed by Redis and a worker process.
- Text-to-image and image editing APIs.
- Generation history with cost and balance source.
- Mock payment flow for local development.

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.10, FastAPI, SQLAlchemy async |
| Database | SQLite for development, PostgreSQL/MySQL compatible for production |
| Migration | Alembic |
| Queue | Redis |
| Frontend | Vue 3, Vite, Pinia, Element Plus |
| Deployment | Docker Compose, Nginx, systemd |

## Billing Model

### Experience Points

Experience points are stored in `users.free_points`.

- Source: daily check-in only.
- Validity: controlled by `FREE_POINTS_TTL_DAYS`, default 10 days.
- Usable for `low` and `medium` quality only.
- Not usable for `high` quality.

### Trial Pack

- Price: `¥5`.
- Quota: `30`.
- Validity: `7` days.
- One purchase per user.
- Uses the same quota pool as subscriptions.

### Subscription Plans

| Plan | Monthly | Yearly | Monthly Quota |
| --- | ---: | ---: | ---: |
| Light | ¥29 | ¥268 | 100 |
| Creator | ¥69 | ¥628 | 350 |
| Pro | ¥149 | ¥1368 | 800 |

Quota cost:

| Quality | Cost |
| --- | ---: |
| low | 1 |
| medium | 2 |
| high | 3 |

Deduction priority:

- `low` and `medium` first try experience points.
- If experience points cannot fully pay the request, subscription quota is used instead.
- `high` always requires subscription quota.
- Professional workflow metadata is reserved with `workflow_type`, `workflow_cost`, and `workflow_preset`.
- The first professional workflow version uses the same quota deduction path and does not create a separate payment product.
- Failed async tasks refund to the original `balance_source`.

## Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

Run the worker in another shell:

```bash
cd backend
python worker.py
```

Run migrations in production-like environments:

```bash
cd backend
alembic upgrade head
```

SQLite development databases are also patched on startup for the current schema.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Build:

```bash
cd frontend
npm run build
```

## Environment

Important backend environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./aigen.db` | Database URL |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | JWT signing key |
| `AI_API_URL` | `https://www.aiartmirror.com/v1` | Image API endpoint |
| `AI_API_KEY` | empty | Image API key |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis queue URL |
| `FREE_POINTS_TTL_DAYS` | `10` | Experience point validity |
| `DEFAULT_WORKFLOW_TYPE` | `standard` | Default generation workflow type |
| `PROFESSIONAL_WORKFLOW_LOW_COST` | `1` | Professional low quality quota cost |
| `PROFESSIONAL_WORKFLOW_MEDIUM_COST` | `2` | Professional medium quality quota cost |
| `PROFESSIONAL_WORKFLOW_HIGH_COST` | `3` | Professional high quality quota cost |
| `GENERATION_MAX_RETRIES` | `2` | Worker retry count |
| `GENERATION_WORKER_CONCURRENCY` | `100` | Worker concurrency |

## Key API Routes

| Method | Path | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register` | Register | No |
| `POST` | `/api/auth/login` | Login | No |
| `POST` | `/api/auth/checkin` | Daily check-in | Yes |
| `GET` | `/api/auth/checkin/status` | Check-in status | Yes |
| `GET` | `/api/points/balance` | Experience points and quota balance | Yes |
| `GET` | `/api/points/plans` | Trial pack and subscription plans | No |
| `GET` | `/api/points/packs` | Deprecated, returns empty list | No |
| `GET` | `/api/membership/plans` | Deprecated, returns empty list | No |
| `POST` | `/api/payment/orders` | Create `trial` or `subscription` order | Yes |
| `POST` | `/api/payment/mock-pay-callback` | Mock payment callback | Yes |
| `POST` | `/api/generate` | Create text-to-image task | Yes |
| `POST` | `/api/edits` | Create image edit task | Yes |
| `GET` | `/api/generate/tasks` | List current user's generation tasks | Yes |
| `GET` | `/api/history` | List generation history | Yes |
| `DELETE` | `/api/history/{id}` | Delete history item | Yes |

## Data Model Notes

Important billing fields:

- `users.free_points`
- `users.free_points_expire_at`
- `users.subscription_plan`
- `users.subscription_period`
- `users.monthly_quota_total`
- `users.monthly_quota_remaining`
- `users.monthly_quota_reset_at`
- `users.trial_activated`
- `users.trial_expire_at`
- `generation_tasks.balance_source`
- `generation_tasks.workflow_type`
- `generation_tasks.workflow_cost`
- `generation_tasks.workflow_preset`
- `generate_histories.balance_source`
- `generate_histories.workflow_type`
- `generate_histories.workflow_cost`
- `generate_histories.workflow_preset`
- `orders.plan_period`

Legacy fields such as `users.points`, `users.is_member`, and `users.member_expire_at` are retained for compatibility, but the generation billing path now uses `QuotaManager`.
