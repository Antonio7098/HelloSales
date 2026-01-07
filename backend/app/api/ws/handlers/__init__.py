"""WebSocket message handlers package.

Individual handler modules (auth, chat, ping, session, skills, voice)
are imported explicitly by the WebSocket router to register their
`@router.handler(...)` functions. This package does not need to export
handler classes.
"""

__all__: list[str] = []
