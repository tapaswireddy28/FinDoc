import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

const ACCEPT = '.pdf,.pptx,.png,.jpg,.jpeg,.gif,.webp,.bmp,.txt,.md'
const HISTORY_KEY = 'rag-history'
const HISTORY_LIMIT = 50
const ACTIVITY_KEY = 'rag-activity'

const NAV = [
  { id: 'ask', label: 'Upload & Ask' },
  { id: 'summarize', label: 'Summarize' },
  { id: 'analyze', label: 'Analyze' },
  { id: 'history', label: 'History' },
  { id: 'streak', label: 'Streak' },
]

const SUGGESTIONS = [
  'What were the total net sales?',
  'What are the key risks?',
  'Break down revenue by segment.',
  'What is the operating income?',
]

function loadJSON(key, fallback, storage = localStorage) {
  try {
    return JSON.parse(storage.getItem(key) || JSON.stringify(fallback))
  } catch {
    return fallback
  }
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : '{}',
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

function dateKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`
}

function calcStreak(set) {
  let s = 0
  const d = new Date()
  if (!set.has(dateKey(d))) d.setDate(d.getDate() - 1) // grace: streak alive until a full day is missed
  while (set.has(dateKey(d))) {
    s++
    d.setDate(d.getDate() - 1)
  }
  return s
}

function sentimentOf(text) {
  const m = /\*\*Sentiment:\*\*\s*(Positive|Neutral|Cautious|Negative)/i.exec(text)
  return m ? m[1].toLowerCase() : null
}

function Output({ text }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked — ignore */
    }
  }
  return (
    <div className="out markdown">
      <button className="copy-btn" onClick={copy} title="Copy to clipboard">
        {copied ? 'Copied ✓' : 'Copy'}
      </button>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  )
}

function NavIcon({ name }) {
  const p = {
    viewBox: '0 0 24 24',
    width: 18,
    height: 18,
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  }
  switch (name) {
    case 'upload':
      return (
        <svg {...p}>
          <path d="M12 15V3" />
          <path d="M7 8l5-5 5 5" />
          <path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
        </svg>
      )
    case 'ask':
      return (
        <svg {...p}>
          <path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.9-.9L3 21l1.9-5.6a8.5 8.5 0 0 1 4-11.3 8.4 8.4 0 0 1 12.1 7.4z" />
        </svg>
      )
    case 'summarize':
      return (
        <svg {...p}>
          <line x1="4" y1="6" x2="20" y2="6" />
          <line x1="4" y1="12" x2="20" y2="12" />
          <line x1="4" y1="18" x2="14" y2="18" />
        </svg>
      )
    case 'analyze':
      return (
        <svg {...p}>
          <line x1="6" y1="20" x2="6" y2="12" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="18" y1="20" x2="18" y2="9" />
        </svg>
      )
    case 'history':
      return (
        <svg {...p}>
          <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
          <path d="M3 3v5h5" />
          <path d="M12 7v5l3 2" />
        </svg>
      )
    case 'streak':
      return (
        <svg {...p}>
          <path d="M12 2c1 3-1 5-2 6s-2 3-2 5a4 4 0 0 0 8 0c0-1-1-3-2-4 0 2-2 3-2 1 0-3 3-4 2-8z" />
        </svg>
      )
    default:
      return null
  }
}

function StreakCalendar({ activity }) {
  const set = new Set(activity)
  const streak = calcStreak(set)
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const startDow = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const monthName = now.toLocaleString('default', { month: 'long', year: 'numeric' })
  const todayD = now.getDate()

  const cells = []
  for (let i = 0; i < startDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <>
      <div className="streak-top">
        <span className="streak-num">{streak}</span>
        <span className="streak-label">
          day{streak === 1 ? '' : 's'} streak
          <br />
          {set.size} active day{set.size === 1 ? '' : 's'} total
        </span>
      </div>
      <div className="cal-month">{monthName}</div>
      <div className="cal-grid">
        {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
          <div key={`dow-${i}`} className="cal-dow">
            {d}
          </div>
        ))}
        {cells.map((d, i) =>
          d === null ? (
            <div key={`b-${i}`} className="cal-cell blank" />
          ) : (
            <div
              key={`d-${d}`}
              className={`cal-cell${set.has(dateKey(new Date(year, month, d))) ? ' active' : ''}${
                d === todayD ? ' today' : ''
              }`}
            >
              {d}
            </div>
          ),
        )}
      </div>
    </>
  )
}

function App() {
  const fileInput = useRef(null)
  const [view, setView] = useState('ask')

  // upload / ingest
  const [over, setOver] = useState(false)
  const [ingest, setIngest] = useState({ msg: '', err: false, busy: false })
  const [ingested, setIngested] = useState(false)
  const [docName, setDocName] = useState('')
  const [chunkCount, setChunkCount] = useState(0)

  // ask
  const [question, setQuestion] = useState('')
  const [ask, setAsk] = useState({ status: '', err: false, busy: false })
  const [answer, setAnswer] = useState('')
  const [pages, setPages] = useState([])

  // voice input (Web Speech API — supported in Chrome/Edge)
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)
  const speechSupported =
    typeof window !== 'undefined' &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition)

  // summarize / analyze
  const [sum, setSum] = useState({ status: '', err: false, busy: false })
  const [summary, setSummary] = useState('')
  const [ana, setAna] = useState({ status: '', err: false, busy: false })
  const [analysis, setAnalysis] = useState('')

  // history is session-only: it clears when the site/tab is closed.
  // activity (the streak) persists across days in localStorage.
  const [history, setHistory] = useState(() => loadJSON(HISTORY_KEY, [], sessionStorage))
  const [activity, setActivity] = useState(() => loadJSON(ACTIVITY_KEY, []))
  useEffect(() => {
    sessionStorage.setItem(HISTORY_KEY, JSON.stringify(history))
  }, [history])
  useEffect(() => {
    localStorage.setItem(ACTIVITY_KEY, JSON.stringify(activity))
  }, [activity])

  const streak = calcStreak(new Set(activity))

  // light / dark theme (persisted). 'system' follows the OS.
  const [theme, setTheme] = useState(() => localStorage.getItem('findoc-theme') || 'system')
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    localStorage.setItem('findoc-theme', theme)
  }, [theme])
  const isDark =
    theme === 'dark' ||
    (theme === 'system' &&
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-color-scheme: dark)').matches)
  function toggleTheme() {
    setTheme(isDark ? 'light' : 'dark')
  }

  function recordActivity() {
    const k = dateKey(new Date())
    setActivity((a) => (a.includes(k) ? a : [...a, k]))
  }

  async function uploadFile(file) {
    if (!file) return
    setIngest({
      msg: `Uploading & ingesting “${file.name}” … (first run downloads the embedder; images use vision OCR)`,
      err: false,
      busy: true,
    })
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: fd })
      const d = await res.json()
      if (!res.ok) throw new Error(d.detail || `HTTP ${res.status}`)
      setIngest({
        msg: `Ingested ${d.chunks} chunk(s) from ${d.source}.`,
        err: false,
        busy: false,
      })
      setIngested(true)
      setDocName(d.source)
      setChunkCount(d.chunks)
      recordActivity()
      setView('ask')
    } catch (e) {
      setIngest({ msg: e.message, err: true, busy: false })
    }
  }

  async function onAsk(qText) {
    const q = (typeof qText === 'string' ? qText : question).trim()
    if (!q) return
    setQuestion(q)
    setAnswer('')
    setPages([])
    setAsk({ status: 'Retrieving and generating…', err: false, busy: true })
    try {
      const d = await postJSON('/api/ask', { question: q })
      setAnswer(d.answer)
      setPages(d.pages || [])
      setAsk({ status: '', err: false, busy: false })
      setHistory((h) =>
        [
          { id: Date.now(), question: q, answer: d.answer, pages: d.pages || [] },
          ...h,
        ].slice(0, HISTORY_LIMIT),
      )
      recordActivity()
    } catch (e) {
      setAsk({ status: e.message, err: true, busy: false })
    }
  }

  function toggleMic() {
    if (!speechSupported) return
    if (listening) {
      recognitionRef.current?.stop()
      return
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.lang = 'en-US'
    rec.interimResults = true
    rec.continuous = false
    rec.onresult = (e) => {
      const text = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join('')
      setQuestion(text)
    }
    rec.onend = () => setListening(false)
    rec.onerror = (e) => {
      setListening(false)
      if (e.error !== 'aborted' && e.error !== 'no-speech') {
        setAsk({ status: `Voice input error: ${e.error}`, err: true, busy: false })
      }
    }
    recognitionRef.current = rec
    setListening(true)
    rec.start()
  }

  async function onSummarize() {
    setSummary('')
    setSum({ status: 'Summarizing the document…', err: false, busy: true })
    try {
      const d = await postJSON('/api/summarize')
      setSummary(d.summary)
      setSum({ status: '', err: false, busy: false })
      recordActivity()
    } catch (e) {
      setSum({ status: e.message, err: true, busy: false })
    }
  }

  async function onAnalyze() {
    setAnalysis('')
    setAna({ status: 'Analyzing the document…', err: false, busy: true })
    try {
      const d = await postJSON('/api/analyze')
      setAnalysis(d.analysis)
      setAna({ status: '', err: false, busy: false })
      recordActivity()
    } catch (e) {
      setAna({ status: e.message, err: true, busy: false })
    }
  }

  function restore(entry) {
    setQuestion(entry.question)
    setAnswer(entry.answer)
    setPages(entry.pages || [])
    setView('ask')
  }

  // Feed the cursor-follow spotlight: set --mx/--my on the hovered card.
  function handleSpotlight(e) {
    const card = e.target.closest('.card')
    if (!card) return
    const r = card.getBoundingClientRect()
    card.style.setProperty('--mx', `${e.clientX - r.left}px`)
    card.style.setProperty('--my', `${e.clientY - r.top}px`)
  }

  const needDoc = !ingested && ['summarize', 'analyze'].includes(view)

  return (
    <div className="app">
      <div className="aurora" aria-hidden="true">
        <span className="blob b1" />
        <span className="blob b2" />
        <span className="blob b3" />
      </div>

      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand">
            <span className="logo-mark" aria-hidden="true">
              <svg viewBox="0 0 48 48" width="26" height="26" fill="none">
                <defs>
                  <linearGradient id="fdm" x1="6" y1="6" x2="42" y2="42" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#c084fc" />
                    <stop offset="1" stopColor="#7c3aed" />
                  </linearGradient>
                </defs>
                <rect width="48" height="48" rx="12" fill="url(#fdm)" />
                <rect x="12" y="27" width="6" height="9" rx="2" fill="#fff" />
                <rect x="21" y="21" width="6" height="15" rx="2" fill="#fff" />
                <rect x="30" y="15" width="6" height="21" rx="2" fill="#fff" />
                <path d="M13 17l7 2.5 6-5 9-3.5" stroke="#fff" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" opacity="0.95" />
              </svg>
            </span>
            <span className="brand-text">FinDoc AI</span>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z" />
              </svg>
            )}
          </button>
        </div>
        <div className="nav-caption">Menu</div>
        <nav className="nav">
          {NAV.map((n) => (
            <button
              key={n.id}
              className={`nav-item${view === n.id ? ' active' : ''}`}
              onClick={() => setView(n.id)}
            >
              <NavIcon name={n.id} />
              <span>{n.label}</span>
              {n.id === 'history' && history.length > 0 && (
                <span className="nav-badge">{history.length}</span>
              )}
              {n.id === 'streak' && streak > 0 && (
                <span className="nav-badge">{streak}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="doc-status">
          <span className={`doc-dot${ingested ? '' : ' off'}`} />
          {ingested ? docName : 'No document yet'}
        </div>
      </aside>

      <div className="content">
        <main onMouseMove={handleSpotlight}>
          {needDoc && (
            <section className="card">
              <p className="notice">
                Upload a document first — head to the <strong>Upload</strong> tab.
              </p>
            </section>
          )}

          {view === 'ask' && (
            <>
            <div className="hero">
              <div className="hero-copy">
                <h1 className="hero-title">
                  Ask your documents,
                  <br />
                  <span className="grad">get grounded answers.</span>
                </h1>
                <p className="hero-sub">
                  Upload a financial report and ask anything — FinDoc AI answers
                  from the document itself, with exact figures and page citations.
                </p>
              </div>
              {speechSupported && (
                <div className="voice">
                  <button
                    type="button"
                    className={`voice-orb${listening ? ' listening' : ''}`}
                    onClick={toggleMic}
                    aria-label={listening ? 'Stop listening' : 'Ask by voice'}
                  >
                    <svg viewBox="0 0 24 24" width="46" height="46" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <rect x="9" y="2" width="6" height="12" rx="3" />
                      <path d="M5 10v1a7 7 0 0 0 14 0v-1" />
                      <line x1="12" y1="18" x2="12" y2="22" />
                    </svg>
                  </button>
                  <div className="voice-cap">{listening ? 'LISTENING…' : 'TAP TO SPEAK'}</div>
                  <div className="voice-sub">Ask by voice — we’ll transcribe it below</div>
                </div>
              )}
            </div>

            <div className="ask-layout">
              <div className="ask-main">
            <section className="card">
              <h2><span className="step">1</span> Upload a document</h2>
              <div
                className={`drop${over ? ' over' : ''}`}
                onClick={() => fileInput.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault()
                  setOver(true)
                }}
                onDragLeave={() => setOver(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setOver(false)
                  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0])
                }}
              >
                <strong>Click to choose</strong> or drag &amp; drop a file here
                <div className="hint">PDF · PPTX · PNG/JPG/WEBP · TXT/MD</div>
              </div>
              <input
                ref={fileInput}
                type="file"
                accept={ACCEPT}
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files.length) uploadFile(e.target.files[0])
                  e.target.value = ''
                }}
              />
              <div className={`status${ingest.err ? ' err' : ''}`}>{ingest.msg}</div>
            </section>

            <section className="card">
              <h2><span className="step">2</span> Ask a question</h2>
              <div className="row">
                <input
                  type="text"
                  placeholder="What are the main points / risks / numbers?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') onAsk()
                  }}
                />
                <button className="action" onClick={() => onAsk()} disabled={ask.busy || !ingested}>
                  {ask.busy ? <span className="spin" /> : 'Ask'}
                </button>
              </div>
              {ingested && (
                <div className="suggestions">
                  <span className="suggest-label">Try</span>
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      className="suggest-chip"
                      onClick={() => onAsk(s)}
                      disabled={ask.busy}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
              {listening && (
                <div className="status">🎙️ Listening… speak your question.</div>
              )}
              <div className={`status${ask.err ? ' err' : ''}`}>{ask.status}</div>
              {answer && <Output text={answer} />}
              {pages.length > 0 && (
                <div className="pages">
                  <span className="pages-label">Sources</span>
                  {pages.map((p) => (
                    <span key={p} className="chip">
                      p. {p}
                    </span>
                  ))}
                </div>
              )}
            </section>
              </div>

              <aside className="rail">
                <div className="rail-card">
                  <div className="rail-title">Document</div>
                  {ingested ? (
                    <>
                      <div className="rail-health">
                        <span className="doc-dot" /> Ready
                      </div>
                      <div className="rail-name" title={docName}>{docName}</div>
                      <ul className="rail-stats">
                        <li><span>Chunks indexed</span><b>{chunkCount}</b></li>
                        <li><span>Q&amp;A</span><b>Enabled</b></li>
                      </ul>
                    </>
                  ) : (
                    <div className="rail-empty">
                      No document loaded yet. Upload one to unlock Q&amp;A, summary,
                      and analysis.
                    </div>
                  )}
                </div>

                <div className="rail-card">
                  <div className="rail-title">This session</div>
                  <ul className="rail-stats">
                    <li><span>Questions asked</span><b>{history.length}</b></li>
                    <li>
                      <span>Current streak</span>
                      <b>{streak} day{streak === 1 ? '' : 's'}</b>
                    </li>
                    <li><span>Active days</span><b>{new Set(activity).size}</b></li>
                  </ul>
                </div>
              </aside>
            </div>
            </>
          )}

          {view === 'summarize' && !needDoc && (
            <section className="card">
              <h2><span className="step">3</span> Summarize the document</h2>
              <button className="action ghost" onClick={onSummarize} disabled={sum.busy}>
                {sum.busy ? <span className="spin" /> : 'Summarize'}
              </button>
              <div className={`status${sum.err ? ' err' : ''}`}>{sum.status}</div>
              {summary && <Output text={summary} />}
            </section>
          )}

          {view === 'analyze' && !needDoc && (
            <section className="card">
              <h2><span className="step">4</span> Analyze the document</h2>
              <p className="card-hint">
                Themes, key entities, notable figures, sentiment, and questions worth
                exploring — grounded in the document with page citations.
              </p>
              <button className="action ghost" onClick={onAnalyze} disabled={ana.busy}>
                {ana.busy ? <span className="spin" /> : 'Analyze'}
              </button>
              <div className={`status${ana.err ? ' err' : ''}`}>{ana.status}</div>
              {analysis && (
                <>
                  {sentimentOf(analysis) && (
                    <div className={`sentiment ${sentimentOf(analysis)}`}>
                      Sentiment: {sentimentOf(analysis)}
                    </div>
                  )}
                  <Output text={analysis} />
                </>
              )}
            </section>
          )}

          {view === 'history' && (
            <section className="card">
              {history.length === 0 ? (
                <>
                  <h2>History</h2>
                  <p className="card-hint">No questions yet. Ask something and it’ll show up here.</p>
                </>
              ) : (
                <>
                  <div className="history-head">
                    <h2>History · {history.length} question(s)</h2>
                    <button className="link" onClick={() => setHistory([])}>
                      Clear
                    </button>
                  </div>
                  <ul className="history">
                    {history.map((h) => (
                      <li key={h.id}>
                        <button className="history-item" onClick={() => restore(h)}>
                          <span className="history-q">{h.question}</span>
                          {h.pages?.length > 0 && (
                            <span className="history-pages">p. {h.pages.join(', ')}</span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          )}

          {view === 'streak' && (
            <section className="card">
              <h2>Your streak</h2>
              <p className="card-hint">
                Every day you use the app counts. Keep the streak alive!
              </p>
              <StreakCalendar activity={activity} />
            </section>
          )}
        </main>

        <footer className="footer">
          FinDoc AI<span className="dot">·</span>grounded answers with page citations
        </footer>
      </div>
    </div>
  )
}

export default App
