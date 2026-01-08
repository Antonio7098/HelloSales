'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  exchangeWorkosCode,
  loadWorkosAuthSession,
  saveWorkosTokens,
  clearWorkosAuthSession,
} from '@/lib/workos/auth'

export default function WorkosCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const oauthError = searchParams.get('error')
        const oauthErrorDescription = searchParams.get('error_description')

        if (oauthError) {
          throw new Error(oauthErrorDescription || oauthError)
        }

        if (!code) {
          throw new Error('Missing WorkOS authorization code')
        }

        const session = await loadWorkosAuthSession()
        if (!session.codeVerifier) {
          throw new Error('Missing PKCE verifier. Please restart sign-in.')
        }

        if (session.state && state && session.state !== state) {
          throw new Error('Invalid auth state. Please restart sign-in.')
        }

        const tokens = await exchangeWorkosCode(code, session.codeVerifier)
        await saveWorkosTokens(tokens)
        await clearWorkosAuthSession()

        // Redirect to home
        router.push('/')
        router.refresh()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to complete sign-in'
        setError(message)
      }
    }

    handleCallback()
  }, [searchParams, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto h-12 w-12 rounded-lg border-2 border-primary flex items-center justify-center mb-4">
            <span className="text-primary font-bold text-lg">HS</span>
          </div>
          <CardTitle>Completing sign-in...</CardTitle>
          <CardDescription>
            {error ? 'An error occurred' : 'Please wait while we complete your sign-in'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="p-3 rounded-md bg-destructive/10 text-destructive text-sm">
              {error}
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
