export async function api(path, data) {
  const response = await fetch('/api' + path, {
    credentials: 'same-origin',
    ...(data !== undefined ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) } : {}),
  })
  const result = await response.json()
  if (!response.ok) throw new Error(result.error || 'Request failed')
  return result
}
