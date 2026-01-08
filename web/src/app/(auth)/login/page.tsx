'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { getWorkosAuthorizationUrl, isWorkosConfigured } from '@/lib/workos/auth'

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const workosConfigured = isWorkosConfigured()

  const handleWorkosLogin = () => {
    setLoading(true)
    const authUrl = getWorkosAuthorizationUrl()
    window.location.href = authUrl
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto h-12 w-12 rounded-lg border-2 border-primary flex items-center justify-center mb-4">
            <span className="text-primary font-bold text-lg">HS</span>
          </div>
          <CardTitle className="text-2xl">Welcome back</CardTitle>
          <CardDescription>Sign in to your HelloSales account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {workosConfigured ? (
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleWorkosLogin}
              disabled={loading}
            >
              {loading ? 'Redirecting...' : 'Sign in with WorkOS SSO'}
            </Button>
          ) : (
            <div className="p-3 rounded-md bg-amber-10 text-amber-600 text-sm">
              WorkOS is not configured. Please set NEXT_PUBLIC_WORKOS_CLIENT_ID in your environment.
            </div>
          )}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
            </div>
          </div>
          <p className="text-sm text-muted-foreground text-center">
            Demo mode: Use any email with password <code>hashed_password</code>
          </p>
        </CardContent>
        <CardFooter>
          <p className="text-sm text-muted-foreground text-center w-full">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="text-primary hover:underline">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
