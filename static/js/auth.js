function saveTokens (data) {
  if (data?.access) localStorage.setItem('vp_access', data.access)
  if (data?.refresh) localStorage.setItem('vp_refresh', data.refresh)
}

function clearTokens () {
  localStorage.removeItem('vp_access')
  localStorage.removeItem('vp_refresh')
}

function loginRedirect () {
  window.location.href = window.VP_URLS.login
}

function routeWithId (template, id) {
  return template.replace(
    '00000000-0000-0000-0000-000000000000',
    encodeURIComponent(id)
  )
}

async function readApiResponse (response) {
  const type = response.headers.get('content-type') || ''
  if (type.includes('application/json')) return response.json()
  await response.text()
  throw new Error(
    response.ok
      ? 'The server returned an unexpected response.'
      : `Server error (${response.status}).`
  )
}

async function vpFetch (url, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } }
  const token = localStorage.getItem('vp_access')
  if (token) opts.headers.Authorization = `Bearer ${token}`
  if (!(opts.body instanceof FormData))
    opts.headers['Content-Type'] =
      opts.headers['Content-Type'] || 'application/json'

  let response = await fetch(url, opts)
  if (response.status === 401 && localStorage.getItem('vp_refresh')) {
    try {
      const refreshResponse = await fetch(window.VP_URLS.authRefresh, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: localStorage.getItem('vp_refresh') })
      })
      if (refreshResponse.ok) {
        const data = await refreshResponse.json()
        saveTokens(data)
        opts.headers.Authorization = `Bearer ${data.access}`
        response = await fetch(url, opts)
      } else {
        clearTokens()
      }
    } catch {
      clearTokens()
    }
  }
  return response
}

async function loadCurrentUser () {
  if (!localStorage.getItem('vp_access')) return null
  try {
    const response = await vpFetch(window.VP_URLS.authMe)
    if (!response.ok) {
      if (response.status === 401) clearTokens()
      return null
    }
    return await readApiResponse(response)
  } catch {
    return null
  }
}

function setupTopbar () {
  const nav = document.getElementById('site-nav')
  if (!nav) return
  const signedOut = document.getElementById('nav-signed-out')
  const signedIn = document.getElementById('nav-signed-in')
  const userName = document.getElementById('nav-user-name')
  const logout = document.getElementById('logout-btn')
  loadCurrentUser().then(user => {
    if (!user) return
    signedOut?.classList.add('hidden')
    signedIn?.classList.remove('hidden')
    if (userName)
      userName.textContent = user.name || user.username || user.email
  })
  logout?.addEventListener('click', () => {
    clearTokens()
    sessionStorage.removeItem('vp_intent')
    window.location.href = window.VP_URLS.home
  })
}

document.addEventListener('DOMContentLoaded', setupTopbar)
