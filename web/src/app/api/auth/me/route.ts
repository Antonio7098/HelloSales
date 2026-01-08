import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const API_URL = process.env.API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    // First try to get token from WorkOS session storage (client-side)
    // The client handles WorkOS tokens, we just proxy to backend

    // Fall back to cookie-based auth for demo mode
    const cookieStore = await cookies()
    const token = cookieStore.get('auth_token')?.value

    if (!token) {
      return NextResponse.json(null, { status: 401 })
    }

    const response = await fetch(`${API_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      return NextResponse.json(null, { status: response.status })
    }

    const user = await response.json()
    return NextResponse.json(user)
  } catch (error) {
    console.error('Get user error:', error)
    return NextResponse.json(
      { error: 'An error occurred' },
      { status: 500 }
    )
  }
}
