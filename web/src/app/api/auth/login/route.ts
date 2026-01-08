import { NextRequest, NextResponse } from 'next/server'
import { saveWorkosTokens, isWorkosConfigured } from '@/lib/workos/auth'

const API_URL = process.env.API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    // Check if WorkOS is configured - if so, use it
    if (isWorkosConfigured()) {
      return NextResponse.json(
        { error: 'Use WorkOS SSO for authentication' },
        { status: 400 }
      )
    }

    const body = await request.json()
    const { email, password } = body

    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Login failed' },
        { status: response.status }
      )
    }

    // Store token in sessionStorage (client-side)
    // The client will read from there and add to Authorization header
    return NextResponse.json(data.user)
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json(
      { error: 'An error occurred during login' },
      { status: 500 }
    )
  }
}
