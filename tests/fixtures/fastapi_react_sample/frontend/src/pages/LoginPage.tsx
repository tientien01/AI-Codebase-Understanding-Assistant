import { login } from '../services/authApi'

export function LoginPage() {
  async function handleSubmit() {
    await login('demo@example.com', 'password')
  }

  return <button onClick={handleSubmit}>Login</button>
}
