import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export default async function Home() {
  const { data, error } = await supabase
    .from('articles')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(20)

  if (error) {
    return (
      <main style={{ maxWidth: 900, margin: '40px auto', padding: 16 }}>
        <h1>Crypto AI News</h1>
        <p>Failed to load articles: {error.message}</p>
      </main>
    )
  }

  return (
    <main style={{ maxWidth: 900, margin: '40px auto', padding: 16 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>Crypto AI News</h1>
      <p style={{ opacity: .7 }}>AI-generated. Not investment advice.</p>
      <div style={{ display: 'grid', gap: 12, marginTop: 16 }}>
        {(data ?? []).map((a: any) => (
          <a key={a.slug} href={`/story/${a.slug}`} style={{ padding: 16, border: '1px solid #ddd', borderRadius: 12, background: '#fff', textDecoration: 'none', color: 'inherit' }}>
            <div style={{ fontSize: 12, opacity: .6, textTransform: 'uppercase' }}>{a.type}</div>
            <div style={{ fontWeight: 600 }}>{a.title}</div>
          </a>
        ))}
        {(!data || data.length === 0) && <div>No articles yet.</div>}
      </div>
    </main>
  )
}
