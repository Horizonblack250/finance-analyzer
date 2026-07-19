import { useState } from 'react'
import { supabase } from '../supabaseClient'

function Login() {
  const [mode, setMode] = useState('login') // login | signup
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [infoMessage, setInfoMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setInfoMessage('')
    setLoading(true)

    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      } else {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        setInfoMessage('Check your email to confirm your account before logging in.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogleLogin() {
    setError('')
    const { error } = await supabase.auth.signInWithOAuth({ provider: 'google' })
    if (error) setError(error.message)
  }

  return (
    <div className="min-h-screen bg-ink-950 flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="font-display font-bold text-2xl text-brass mb-1">Smart Budget Analyzer</div>
          <div className="text-paper-dim text-sm">
            {mode === 'login' ? 'Log in to see your spending' : 'Create an account to get started'}
          </div>
        </div>

        <button
          onClick={handleGoogleLogin}
          className="w-full bg-paper text-ink-950 font-medium py-3 rounded-full mb-4
                     hover:bg-brass-bright transition-colors flex items-center justify-center gap-2"
        >
          Continue with Google
        </button>

        <div className="flex items-center gap-3 my-5">
          <div className="flex-1 h-px bg-ink-700" />
          <span className="text-xs text-paper-dim">or</span>
          <div className="flex-1 h-px bg-ink-700" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="w-full bg-ink-900 border border-ink-700 rounded-full p-3 px-5 text-paper placeholder:text-paper-dim/50"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            minLength={8}
            className="w-full bg-ink-900 border border-ink-700 rounded-full p-3 px-5 text-paper placeholder:text-paper-dim/50"
          />

          {error && <div className="text-brick text-sm px-2">{error}</div>}
          {infoMessage && <div className="text-emerald text-sm px-2">{infoMessage}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brass text-ink-950 font-medium py-3 rounded-full
                       disabled:opacity-40 hover:bg-brass-bright transition-colors"
          >
            {loading ? 'Please wait...' : mode === 'login' ? 'Log In' : 'Sign Up'}
          </button>
        </form>

        <div className="text-center mt-5 text-sm text-paper-dim">
          {mode === 'login' ? (
            <>
              Don't have an account?{' '}
              <button onClick={() => setMode('signup')} className="text-brass hover:underline">Sign up</button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button onClick={() => setMode('login')} className="text-brass hover:underline">Log in</button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default Login
