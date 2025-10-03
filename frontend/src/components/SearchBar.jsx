import React, { useEffect, useMemo, useState } from 'react'

export function SearchBar({ value, onChange, loading, disabled }){
  const [q, setQ] = useState(value||'')

  useEffect(()=> setQ(value||''), [value])

  useEffect(()=>{
    const id = setTimeout(()=>{
      if(q && q.length>1) onChange?.(q)
    }, 300)
    return ()=> clearTimeout(id)
  }, [q])

  return (
    <div className="hstack" style={{width:'100%'}}>
      <input className="input" placeholder="Ask a question..." value={q} onChange={e=>setQ(e.target.value)} disabled={disabled} />
      <button className="button secondary" disabled>
        {loading? 'Searching...' : 'Search'}
      </button>
    </div>
  )
}



