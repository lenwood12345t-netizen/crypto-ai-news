import { createClient } from '@supabase/supabase-js'
import { notFound } from 'next/navigation'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export default async function Story({ params }:{ params:{ slug:string } }) {
  const { data, error } = await supabase
    .from('articles')
    .select('*')
    .eq('slug', params.slug)
    .single()

  if (error || !data) return notFound()

  const json = data.json_payload as any

  return (
    <main style={{ maxWidth: 800, margin: '40px auto', padding: 16 }}>
      <a href="/" style={{ display:'inline-block', marginBottom: 12 }}>&larr; Back</a>
      <h1 style={{ fontSize: 24, fontWeight: 700 }}>{data.title}</h1>

      {/* body_md already contains HTML/markdown rendered to HTML */}
      <article dangerouslySetInnerHTML={{ __html: data.body_md }} />

      {Array.isArray(json?.sources) && (
        <section style={{ marginTop: 24 }}>
          <h3>Sources</h3>
          <ul>
            {json.sources.map((s:any) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.publisher || 'Source'} — {s.title}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
