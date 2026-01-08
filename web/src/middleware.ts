import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes that don't require authentication
const publicPaths = [
  '/login',
  '/register',
  '/auth/workos/callback',
  '/api/auth/',
  '/api/health',
]

// Check if a path is public
function isPublicPath(path: string): boolean {
  return publicPaths.some((publicPath) => path.startsWith(publicPath))
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths
  if (isPublicPath(pathname)) {
    return NextResponse.next()
  }

  // Check for authentication
  // For WorkOS auth, the token is stored in sessionStorage (client-side)
  // So we need to check via a server-side endpoint or cookie

  // Check for auth_token cookie (for demo mode)
  const authToken = request.cookies.get('auth_token')?.value

  if (!authToken) {
    // Redirect to login
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
  ],
}
