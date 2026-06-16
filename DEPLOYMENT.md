# Deploying NexusAI to Production

This guide walks you through deploying **NexusAI** to production using managed cloud platforms:
* **Frontend**: Next.js deployed on **Vercel**
* **Backend**: FastAPI (with Docker) deployed on **Render**
* **Databases**: Managed cloud instances of **PostgreSQL**, **Redis**, and **Qdrant Cloud**

---

## 1. Database Provisioning

### Managed PostgreSQL & Redis (Render / Railway)
Provision production-grade SQL and caching databases:
1. **Render**:
   * Go to your dashboard and select **New** -> **PostgreSQL**.
   * Copy the **Internal Database URL** (for backend services within Render) or **External Database URL** (for remote access).
   * Go to **New** -> **Redis**.
   * Copy the connection URL.
2. OR **Railway**:
   * Create a new project, select **Provision PostgreSQL** and **Provision Redis**.
   * Copy their respective connection URLs (`DATABASE_URL` and `REDIS_URL`).

### Managed Vector DB (Qdrant Cloud)
To run document similarity searches in production:
1. Register at [Qdrant Cloud](https://cloud.qdrant.io/) (includes a free cluster with 1GB storage).
2. Create a cluster and copy:
   * **Host URL** (e.g., `xxxx-xxxx.eu-central.aws.qdrant.io`)
   * **API Key** (if enabled)

---

## 2. Backend Deployment (Render)

Render will build and run the backend using the multi-stage `backend/Dockerfile` automatically.

### Steps:
1. Log in to [Render](https://render.com/) and click **New** -> **Web Service**.
2. Connect your GitHub repository (`titanShubh/NexusAI`).
3. Configure settings:
   * **Root Directory**: `backend`
   * **Runtime**: `Docker`
   * **Dockerfile Path**: `Dockerfile` (relative to the `backend` root)
4. Add the following **Environment Variables**:
   * `OPENAI_API_KEY`: Your OpenAI API key (required for RAG embeddings and agent routing).
   * `DATABASE_URL`: Your production PostgreSQL connection string.
   * `REDIS_URL`: Your production Redis connection string.
   * `QDRANT_HOST`: Your Qdrant Cloud host URL.
   * `QDRANT_PORT`: `6333` (or the port specified by Qdrant Cloud)
   * `JWT_SECRET`: A secure random hex string (generate via `openssl rand -hex 32`).
   * `CORS_ORIGINS`: JSON list pointing to your future Vercel URL (e.g. `["https://nexus-ai.vercel.app"]`).
5. Click **Deploy**. Copy the deployed backend URL (e.g. `https://nexus-ai-backend.onrender.com`).

---

## 3. Frontend Deployment (Vercel)

Vercel is optimized for Next.js applications and deploys directly from your Git pushes.

### Steps:
1. Log in to [Vercel](https://vercel.com/) and click **Add New** -> **Project**.
2. Select your `titanShubh/NexusAI` repository.
3. Configure project settings:
   * **Framework Preset**: `Next.js`
   * **Root Directory**: `frontend`
4. Add the **Environment Variables**:
   * `NEXT_PUBLIC_API_URL`: The URL of your deployed backend service + `/api` (e.g., `https://nexus-ai-backend.onrender.com/api`).
5. Click **Deploy**. Vercel will build the frontend and provide you with a production URL (e.g. `https://nexus-ai.vercel.app`).

*Note: Remember to update the `CORS_ORIGINS` environment variable in your Render backend settings once your Vercel URL is active, and trigger a quick redeployment.*

---

## 4. Verification

1. Visit your Vercel frontend URL.
2. Sign up / Register a new user (which automatically creates the database tables).
3. Go to the **Document Catalog**, upload `Assignment-1 DAA.pdf` or any document.
4. Try querying *"plot a graph of number of questions vs topic"* to verify that RAG search, structured data extraction, and visual analytics charts function cleanly in production!
