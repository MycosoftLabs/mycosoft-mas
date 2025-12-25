import { NextResponse, type NextRequest } from "next/server"

function isProtectedPath(pathname: string) {
  return (
    pathname === "/myca" ||
    pathname.startsWith("/myca/") ||
    pathname === "/n8n" ||
    pathname.startsWith("/n8n/")
  )
}

export function middleware(req: NextRequest) {
  if (!isProtectedPath(req.nextUrl.pathname)) return NextResponse.next()

  const staffToken = process.env.MYCA_STAFF_TOKEN
  if (!staffToken) return NextResponse.next()

  const authHeader = req.headers.get("authorization") ?? ""
  const bearer = authHeader.startsWith("Bearer ") ? authHeader.slice("Bearer ".length) : null
  const cookieToken = req.cookies.get("myca_staff_token")?.value ?? null
  const queryToken = req.nextUrl.searchParams.get("token")

  if (queryToken && queryToken === staffToken) {
    const url = req.nextUrl.clone()
    url.searchParams.delete("token")
    const res = NextResponse.redirect(url)
    res.cookies.set("myca_staff_token", staffToken, { httpOnly: true, sameSite: "lax", path: "/" })
    return res
  }

  if (bearer === staffToken || cookieToken === staffToken) return NextResponse.next()

  const redirectUrl = req.nextUrl.clone()
  redirectUrl.pathname = "/"
  redirectUrl.searchParams.set("error", "unauthorized")
  return NextResponse.redirect(redirectUrl)
}

export const config = {
  matcher: ["/myca/:path*", "/n8n/:path*"],
}
