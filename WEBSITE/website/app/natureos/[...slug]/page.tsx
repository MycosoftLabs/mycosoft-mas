import { DashboardHeader } from "@/components/dashboard/header"
import { DashboardShell } from "@/components/dashboard/shell"

interface NatureOSSubpageProps {
  params: Promise<{ slug: string[] }>
}

export default async function NatureOSSubpage({ params }: NatureOSSubpageProps) {
  const { slug } = await params
  const path = `/natureos/${slug.join("/")}`

  return (
    <DashboardShell>
      <DashboardHeader heading="NatureOS" text={`This section is coming soon: ${path}`} />
      <div className="mt-6 rounded-lg border border-gray-800 bg-black/20 p-4 text-sm text-gray-200">
        This route is part of the NatureOS dashboard navigation but is not implemented yet in this repo.
      </div>
    </DashboardShell>
  )
}


