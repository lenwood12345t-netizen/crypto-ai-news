import { supabase } from '@/lib/db'
import { notFound } from 'next/navigation'

export default async function Story({ params }:{ params:{ slug:string } }) {
  const { data } = await supabase.from('articles').select('*').eq('slug', params.slug).single()
  if(!data) return notFound()
  const json = data.json_payload as any
  return (
    <main style={{maxWidth:800, margin:'40px auto', padding:16, fontFamily:'system-ui'}}>
      <h1 style={{fontSize:24, fontWeight:700}}>{data.title}</h1>
      <article dangerouslySetInnerHTML={{ __html: data.body_md }} />
      {Array.isArray(json?.sources) && (
        <section>
          <h3>Sources</h3>
          <ul>
            {json.sources.map((s:any)=>(
              <li key={s.url}><a href={s.url} target="_blank">{s.publisher || 'Source'} — {s.title}</a></li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
