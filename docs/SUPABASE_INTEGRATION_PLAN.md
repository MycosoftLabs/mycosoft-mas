# SUPABASE INTEGRATION PLAN FOR MYCOSOFT

**Document Version**: 1.0.0  
**Date**: 2026-01-17  
**Classification**: Internal - Technical Integration Plan  
**Author**: AI Development Agent  
**Status**: ✅ APPROVED FOR IMPLEMENTATION

---

## 📋 EXECUTIVE SUMMARY

This document outlines the comprehensive integration plan for Supabase into the Mycosoft platform. Supabase provides a complete backend-as-a-service that will enhance our existing infrastructure with managed authentication, realtime data synchronization, vector embeddings for AI/ML, edge functions, and more.

### Supabase Project Details

| Property | Value |
|----------|-------|
| Project URL | `https://hnevnsxnhfibhbsipqvz.supabase.co` |
| Publishable Key | `sb_publishable_CKkfrniLH2865uGRsVKr7g_w5CVl1FI` |
| Plan | Pro ($25/month) |
| Monthly Active Users | 100,000 |
| Disk Size | 8 GB |
| Egress | 250 GB |
| File Storage | 100 GB |
| Backup | Daily (7-day retention) |

---

## 🎯 SUPABASE CAPABILITIES OVERVIEW

### 1. Authentication (Priority: 🔴 CRITICAL)

| Feature | Status | Description |
|---------|--------|-------------|
| Email Login | GA | Magic links & password-based |
| Social Login | GA | Google, GitHub, Discord, etc. |
| Phone Login | GA | SMS-based authentication |
| Passwordless | GA | Magic link authentication |
| SAML SSO | GA | Enterprise single sign-on |
| Multi-Factor Auth | GA | TOTP, SMS, WebAuthn |
| Row Level Security | GA | Fine-grained access control |
| CAPTCHA | GA | Bot protection |
| Server-Side Auth | Beta | Next.js, SvelteKit helpers |

**Use Case for Mycosoft:**
- User authentication for mycosoft.com
- Device ownership verification for MycoBrain
- API access control for MINDEX
- Team/organization management for enterprises

### 2. Database & Postgres (Priority: 🔴 CRITICAL)

| Feature | Status | Description |
|---------|--------|-------------|
| Full Postgres | GA | Complete PostgreSQL database |
| PostgREST API | GA | Auto-generated REST API |
| GraphQL API | GA | pg_graphql extension |
| Database Webhooks | Beta | Trigger external services |
| Vault | Alpha | Secrets encryption |
| Row Level Security | GA | Fine-grained policies |

**Use Case for Mycosoft:**
- Complement/migrate MINDEX data
- Store user profiles and preferences
- Device telemetry storage
- Taxonomy and species data

### 3. Vector Database & AI (Priority: 🔴 CRITICAL)

| Feature | Status | Description |
|---------|--------|-------------|
| pgvector | GA | Vector embeddings storage |
| Vector Search | GA | Similarity search |
| LangChain Integration | GA | RAG & AI pipelines |
| Hybrid Search | GA | Vector + full-text |

**Use Case for Mycosoft:**
- MYCA chatbot knowledge base
- Species similarity search
- Document embeddings for search
- Research paper embeddings
- Smell/scent embeddings for MycoBrain

### 4. Realtime (Priority: 🟡 HIGH)

| Feature | Status | Description |
|---------|--------|-------------|
| Postgres Changes | GA | Database change subscriptions |
| Broadcast | GA | User-to-user messaging |
| Presence | GA | Online status tracking |
| Authorization | Beta | Secure realtime |

**Use Case for Mycosoft:**
- Live MycoBrain telemetry
- Real-time dashboard updates
- Collaborative features
- Device status indicators

### 5. Storage (Priority: 🟡 HIGH)

| Feature | Status | Description |
|---------|--------|-------------|
| File Storage | GA | S3-compatible storage |
| CDN | GA | Global content delivery |
| Image Transforms | GA | Resize, crop on-the-fly |
| Resumable Uploads | GA | Large file handling |
| S3 Compatibility | GA | Direct S3 API access |

**Use Case for Mycosoft:**
- Species images storage
- User avatars
- Document storage
- MycoBrain firmware binaries
- Research paper PDFs

### 6. Edge Functions (Priority: 🟢 MEDIUM)

| Feature | Status | Description |
|---------|--------|-------------|
| Deno Functions | GA | Globally distributed |
| NPM Support | GA | Node.js packages |
| Regional Invocation | GA | Low-latency execution |
| Webhooks | GA | Stripe, GitHub, etc. |

**Use Case for Mycosoft:**
- Stripe payment webhooks
- MycoBrain command processing
- AI/LLM API orchestration
- Email notifications

### 7. Additional Features

| Feature | Status | Description |
|---------|--------|-------------|
| Branching | Beta | Preview environments |
| Read Replicas | GA | Multi-region |
| Log Drains | Alpha | External logging |
| Terraform | Alpha | Infrastructure as Code |
| MCP Integration | Alpha | Cursor/AI tools |

---

## 🔄 INTEGRATION WITH EXISTING MYCOSOFT SYSTEMS

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT MYCOSOFT STACK                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐ │
│  │   Website   │   │   MINDEX    │   │   MAS Orchestrator      │ │
│  │  (Next.js)  │   │  (FastAPI)  │   │    (LangChain/n8n)      │ │
│  │   :3000     │   │    :8000    │   │       :8001             │ │
│  └─────────────┘   └─────────────┘   └─────────────────────────┘ │
│         │                │                      │                 │
│         └────────────────┼──────────────────────┘                 │
│                          │                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    PostgreSQL (MINDEX)                       │ │
│  │                         :5433                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐ │
│  │  Qdrant     │   │   Redis     │   │   MycoBrain Service     │ │
│  │   :6345     │   │   :6390     │   │       :8003             │ │
│  └─────────────┘   └─────────────┘   └─────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed Supabase-Enhanced Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 SUPABASE-ENHANCED MYCOSOFT STACK                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    SUPABASE CLOUD                            │ │
│  │  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │ │
│  │  │   Auth   │ Database │ Realtime │ Storage  │ Edge Fn  │   │ │
│  │  │          │ + Vector │          │ + CDN    │          │   │ │
│  │  └──────────┴──────────┴──────────┴──────────┴──────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐ │
│  │   Website   │   │   MINDEX    │   │   MAS Orchestrator      │ │
│  │  (Next.js)  │◄──│  (FastAPI)  │◄──│    (LangChain/n8n)      │ │
│  │   :3000     │   │    :8000    │   │       :8001             │ │
│  └─────────────┘   └─────────────┘   └─────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           LOCAL INFRASTRUCTURE (Kept for redundancy)         │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │ │
│  │  │ PostgreSQL  │   │   Qdrant    │   │ MycoBrain Svc   │    │ │
│  │  │  (backup)   │   │  (backup)   │   │    :8003        │    │ │
│  │  └─────────────┘   └─────────────┘   └─────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📅 INTEGRATION PHASES

### Phase 1: Authentication (Week 1-2) 🔴 CRITICAL

**Objective:** Replace/add Supabase Auth to the website

#### Tasks:
1. Install Supabase SDK in Next.js website
2. Configure environment variables
3. Create auth middleware for App Router
4. Implement login/signup pages
5. Add social login providers (Google, GitHub)
6. Implement protected routes
7. Add user profile management
8. Integrate with MycoBrain device ownership

#### Files to Create/Modify:
```
website/
├── lib/
│   └── supabase/
│       ├── client.ts          # Browser client
│       ├── server.ts          # Server client  
│       └── middleware.ts      # Auth middleware
├── app/
│   ├── auth/
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   ├── callback/route.ts
│   │   └── logout/route.ts
│   └── middleware.ts
├── components/
│   └── auth/
│       ├── LoginForm.tsx
│       ├── SignupForm.tsx
│       ├── SocialLogin.tsx
│       └── UserMenu.tsx
└── .env.local                 # Supabase credentials
```

#### Environment Variables:
```env
NEXT_PUBLIC_SUPABASE_URL=https://hnevnsxnhfibhbsipqvz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_CKkfrniLH2865uGRsVKr7g_w5CVl1FI
SUPABASE_SERVICE_ROLE_KEY=<from_dashboard>
```

---

### Phase 2: Database & Vector Store (Week 2-3) 🔴 CRITICAL

**Objective:** Set up Supabase Postgres for user data and vectors

#### Tasks:
1. Enable pgvector extension
2. Create user profiles table with RLS
3. Create documents table for RAG
4. Create vector embeddings table
5. Set up LangChain integration
6. Migrate critical MINDEX data (optional)
7. Implement hybrid search

#### Database Schema:
```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- User profiles (auto-linked to auth.users)
CREATE TABLE profiles (
  id UUID REFERENCES auth.users NOT NULL PRIMARY KEY,
  username TEXT UNIQUE,
  full_name TEXT,
  avatar_url TEXT,
  organization TEXT,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT username_length CHECK (char_length(username) >= 3)
);

-- MycoBrain devices
CREATE TABLE devices (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  device_name TEXT NOT NULL,
  device_type TEXT DEFAULT 'mycobrain',
  mac_address TEXT UNIQUE,
  last_seen TIMESTAMPTZ,
  config JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents for RAG/search
CREATE TABLE documents (
  id BIGSERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  embedding VECTOR(1536),  -- OpenAI embedding size
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Telemetry data
CREATE TABLE telemetry (
  id BIGSERIAL PRIMARY KEY,
  device_id UUID REFERENCES devices,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  temperature FLOAT,
  humidity FLOAT,
  pressure FLOAT,
  gas_resistance FLOAT,
  iaq FLOAT,
  co2 FLOAT,
  voc FLOAT,
  raw_data JSONB
);

-- Species/Taxonomy (from MINDEX)
CREATE TABLE species (
  id BIGSERIAL PRIMARY KEY,
  scientific_name TEXT NOT NULL,
  common_name TEXT,
  kingdom TEXT,
  phylum TEXT,
  class TEXT,
  order_name TEXT,
  family TEXT,
  genus TEXT,
  species_epithet TEXT,
  description TEXT,
  embedding VECTOR(1536),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Public profiles are viewable by everyone" 
  ON profiles FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" 
  ON profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own devices" 
  ON devices FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own devices" 
  ON devices FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own telemetry" 
  ON telemetry FOR SELECT 
  USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

-- Vector search function (for LangChain)
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5,
  filter JSONB DEFAULT '{}'
) RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE documents.metadata @> filter
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

---

### Phase 3: Realtime & Live Data (Week 3-4) 🟡 HIGH

**Objective:** Enable real-time updates for MycoBrain and dashboards

#### Tasks:
1. Set up Supabase Realtime subscriptions
2. Implement live telemetry streaming
3. Add device status presence
4. Create collaborative features
5. Update CREP dashboard with realtime

#### Implementation:
```typescript
// lib/supabase/realtime.ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Subscribe to telemetry changes
export function subscribeToTelemetry(deviceId: string, callback: (data: any) => void) {
  return supabase
    .channel(`telemetry:${deviceId}`)
    .on('postgres_changes', 
      { event: 'INSERT', schema: 'public', table: 'telemetry', filter: `device_id=eq.${deviceId}` },
      callback
    )
    .subscribe()
}

// Device presence
export function trackDevicePresence(deviceId: string) {
  return supabase.channel('devices')
    .on('presence', { event: 'sync' }, () => {
      const state = supabase.channel('devices').presenceState()
      console.log('Online devices:', state)
    })
    .subscribe(async (status) => {
      if (status === 'SUBSCRIBED') {
        await supabase.channel('devices').track({ device_id: deviceId, online_at: new Date() })
      }
    })
}
```

---

### Phase 4: Storage Integration (Week 4-5) 🟡 HIGH

**Objective:** Migrate image and file storage to Supabase

#### Tasks:
1. Create storage buckets (images, documents, firmware)
2. Set up storage policies
3. Implement image upload components
4. Add CDN for species images
5. Migrate existing images (optional)

#### Storage Buckets:
```sql
-- Create buckets
INSERT INTO storage.buckets (id, name, public) VALUES 
  ('avatars', 'avatars', true),
  ('species-images', 'species-images', true),
  ('documents', 'documents', false),
  ('firmware', 'firmware', false);

-- Public bucket policies
CREATE POLICY "Avatar images are publicly accessible" 
  ON storage.objects FOR SELECT USING (bucket_id = 'avatars');

CREATE POLICY "Users can upload own avatar" 
  ON storage.objects FOR INSERT WITH CHECK (
    bucket_id = 'avatars' AND 
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Species images are publicly accessible" 
  ON storage.objects FOR SELECT USING (bucket_id = 'species-images');
```

---

### Phase 5: Edge Functions & Webhooks (Week 5-6) 🟢 MEDIUM

**Objective:** Deploy serverless functions for payments and processing

#### Tasks:
1. Set up Stripe webhook handler
2. Create email notification function
3. Implement AI/LLM orchestration
4. Add MycoBrain command processing

#### Edge Function: Stripe Webhooks
```typescript
// supabase/functions/stripe-webhooks/index.ts
import Stripe from 'https://esm.sh/stripe@14?target=denonext'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const stripe = new Stripe(Deno.env.get('STRIPE_API_KEY')!, {
  apiVersion: '2024-11-20'
})

const cryptoProvider = Stripe.createSubtleCryptoProvider()

Deno.serve(async (request) => {
  const signature = request.headers.get('Stripe-Signature')!
  const body = await request.text()
  
  try {
    const event = await stripe.webhooks.constructEventAsync(
      body,
      signature,
      Deno.env.get('STRIPE_WEBHOOK_SIGNING_SECRET')!,
      undefined,
      cryptoProvider
    )
    
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )
    
    switch (event.type) {
      case 'checkout.session.completed':
        // Handle successful payment
        const session = event.data.object
        await supabase.from('subscriptions').upsert({
          user_id: session.metadata?.user_id,
          stripe_customer_id: session.customer,
          status: 'active',
          plan: session.metadata?.plan
        })
        break
      // ... handle other events
    }
    
    return new Response(JSON.stringify({ ok: true }), { status: 200 })
  } catch (err) {
    return new Response(err.message, { status: 400 })
  }
})
```

---

### Phase 6: AI/ML & LangChain Integration (Week 6-8) 🔴 CRITICAL

**Objective:** Integrate LangChain with Supabase vectors for MYCA

#### Tasks:
1. Set up LangChain with Supabase vector store
2. Create document ingestion pipeline
3. Implement RAG for MYCA chatbot
4. Add semantic search for species
5. Integrate with MAS orchestrator

#### LangChain Integration:
```typescript
// lib/langchain/supabase-store.ts
import { SupabaseVectorStore } from '@langchain/community/vectorstores/supabase'
import { OpenAIEmbeddings } from '@langchain/openai'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const embeddings = new OpenAIEmbeddings({
  openAIApiKey: process.env.OPENAI_API_KEY
})

export const vectorStore = new SupabaseVectorStore(embeddings, {
  client: supabase,
  tableName: 'documents',
  queryName: 'match_documents'
})

// Add documents
export async function addDocuments(docs: string[], metadata: any[]) {
  return await vectorStore.addDocuments(
    docs.map((content, i) => ({
      pageContent: content,
      metadata: metadata[i]
    }))
  )
}

// Semantic search
export async function semanticSearch(query: string, k = 5, filter = {}) {
  return await vectorStore.similaritySearch(query, k, filter)
}

// RAG for MYCA
export async function ragQuery(userQuery: string) {
  const relevantDocs = await semanticSearch(userQuery, 5)
  const context = relevantDocs.map(doc => doc.pageContent).join('\n\n')
  
  // Use context with LLM
  return { context, docs: relevantDocs }
}
```

---

## 🔐 SECURITY CONSIDERATIONS

### Environment Variables (NEVER commit)
```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://hnevnsxnhfibhbsipqvz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=<secret>

# Stripe
STRIPE_API_KEY=<secret>
STRIPE_WEBHOOK_SIGNING_SECRET=<secret>

# OpenAI
OPENAI_API_KEY=<secret>
```

### Row Level Security (RLS) Best Practices
1. **Always enable RLS** on tables with user data
2. **Use service role key** only on server-side
3. **Never expose service key** to client
4. **Validate JWT** in Edge Functions
5. **Use policies** for all CRUD operations

### API Key Rotation Schedule
| Key Type | Rotation Frequency | Notes |
|----------|-------------------|-------|
| Publishable Key | Yearly | Safe to expose |
| Service Role Key | Quarterly | Server-side only |
| Stripe Keys | When compromised | Store in vault |
| OpenAI Key | Quarterly | Rate limit monitoring |

---

## 📊 COST ANALYSIS

### Supabase Pro Plan ($25/month)

| Resource | Included | Expected Usage | Status |
|----------|----------|----------------|--------|
| Monthly Active Users | 100,000 | ~1,000 | ✅ OK |
| Database Size | 8 GB | ~2 GB | ✅ OK |
| Storage | 100 GB | ~10 GB | ✅ OK |
| Egress | 250 GB | ~50 GB | ✅ OK |
| Edge Function Invocations | 2M | ~100K | ✅ OK |
| Realtime Connections | Unlimited | ~500 | ✅ OK |

### Additional Costs (Usage-based)
- Extra Database: $0.125/GB/month
- Extra Egress: $0.09/GB
- Extra MAUs: $0.00325/MAU

**Estimated Monthly Cost: $25-50**

---

## 🎯 SUCCESS METRICS

### Phase 1 (Auth)
- [ ] User can sign up with email
- [ ] User can login with Google/GitHub
- [ ] Protected routes work correctly
- [ ] Session persists across refreshes
- [ ] MycoBrain device can be linked to user

### Phase 2 (Database)
- [ ] User profiles created on signup
- [ ] Vector search returns relevant results
- [ ] RLS policies working correctly
- [ ] Device telemetry stored successfully

### Phase 3 (Realtime)
- [ ] Live telemetry updates in dashboard
- [ ] Device presence shows online/offline
- [ ] Subscriptions don't leak data

### Phase 4 (Storage)
- [ ] Images upload successfully
- [ ] CDN serving images globally
- [ ] Access control working

### Phase 5 (Edge Functions)
- [ ] Stripe webhooks processed
- [ ] Payments create subscriptions
- [ ] Email notifications sent

### Phase 6 (AI/LangChain)
- [ ] Documents indexed with embeddings
- [ ] MYCA can answer questions using RAG
- [ ] Species search returns similar matches

---

## 📝 NEXT STEPS

1. **Immediate (Today)**
   - [x] Create integration plan document
   - [ ] Install Supabase SDK in website
   - [ ] Configure environment variables

2. **This Week**
   - [ ] Implement basic auth flow
   - [ ] Create database schema
   - [ ] Set up RLS policies

3. **Next Week**
   - [ ] Add social login
   - [ ] Enable pgvector
   - [ ] Implement realtime

4. **Month 1**
   - [ ] Complete all phases
   - [ ] Full testing
   - [ ] Production deployment

---

## 📚 REFERENCES

- [Supabase Documentation](https://supabase.com/docs)
- [Next.js App Router Auth](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [LangChain + Supabase](https://supabase.com/docs/guides/ai/langchain)
- [Stripe Webhooks](https://supabase.com/docs/guides/functions/examples/stripe-webhooks)
- [pgvector Guide](https://supabase.com/docs/guides/database/extensions/pgvector)

---

**Document Created**: 2026-01-17  
**Last Updated**: 2026-01-17  
**Author**: AI Development Agent  
**Approved By**: Pending
