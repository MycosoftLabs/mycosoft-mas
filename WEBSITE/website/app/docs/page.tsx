import Link from "next/link"

export default function DocsPage() {
  return (
    <div className="container mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">Documentation</h1>
      <p className="mt-2 text-muted-foreground">
        Local docs are not published yet in this repo. This page exists to avoid broken navigation during local
        development.
      </p>

      <div className="mt-6 rounded-lg border p-4">
        <p className="text-sm text-muted-foreground">Useful entry points:</p>
        <ul className="mt-3 list-disc pl-5 text-sm">
          <li>
            <Link className="underline" href="/natureos">
              NatureOS Dashboard
            </Link>
          </li>
          <li>
            <Link className="underline" href="/apps">
              Apps
            </Link>
          </li>
          <li>
            <Link className="underline" href="/devices">
              Devices
            </Link>
          </li>
        </ul>
      </div>
    </div>
  )
}


