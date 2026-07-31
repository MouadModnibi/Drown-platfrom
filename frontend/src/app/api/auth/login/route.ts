import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch('http://127.0.0.1:5000/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json({ error: data.error || 'Login failed' }, { status: res.status });
    }

    // Fetch full user info (including is_admin) so the client can populate
    // the auth context without a separate /auth/me round-trip.
    let userInfo = { id: 0, username: data.username, is_admin: false };
    try {
      const meRes = await fetch('http://127.0.0.1:5000/api/auth/me', {
        headers: { Authorization: `Bearer ${data.token}` },
      });
      if (meRes.ok) {
        const meData = await meRes.json();
        userInfo = meData.user ?? userInfo;
      }
    } catch {
      // Non-fatal — client will re-fetch on next page load
    }

    const response = NextResponse.json({
      success: true,
      id: userInfo.id,
      username: userInfo.username,
      is_admin: userInfo.is_admin,
    });

    // Set secure httpOnly cookie containing the API token
    response.cookies.set({
      name: 'auth_token',
      value: data.token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    return response;
  } catch (error: any) {
    return NextResponse.json({ error: error.message || 'Server error' }, { status: 500 });
  }
}
