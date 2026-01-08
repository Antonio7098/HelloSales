import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const publicPaths = ['/login', '/register', '/api/auth/login', '/api/auth/register']
const apiPaths = ['/api/']

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname
  const token = request.cookies.get('auth_token')?.value

  // Allow public paths
  if (publicPaths.some(p => path.startsWith(p))) {
    return NextResponse.next()
  }

  // Check API routes
  if (apiPaths.some(p => path.startsWith(p))) {
    // Allow health check and auth APIs
    if (path.startsWith('/api/auth/') || path.startsWith('/health')) {
      return NextResponse.next()
    }
    
    // Require auth for other API routes
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    return NextResponse.next()
  }

  // Require auth for dashboard routes
  if (path.startsWith('/(dashboard)') && !token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', path)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.png$).*)',
  ],
}
