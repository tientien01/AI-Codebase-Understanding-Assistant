import {
  BarChart3,
  Bell,
  Check,
  CircleHelp,
  Clock,
  Code2,
  Folder,
  GitBranch,
  Grid2X2,
  Home,
  Layers,
  List,
  MoreHorizontal,
  Network,
  Pause,
  Plus,
  RefreshCw,
  Search as SearchIcon,
  Settings,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Star,
  Target,
  TriangleAlert,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { IconName } from '../../types/api'

const icons: Record<IconName, LucideIcon> = {
  home: Home,
  folder: Folder,
  clock: Clock,
  star: Star,
  layers: Layers,
  settings: Settings,
  nodes: Network,
  share: Share2,
  sliders: SlidersHorizontal,
  spark: Sparkles,
  target: Target,
  search: SearchIcon,
  chart: BarChart3,
  code: Code2,
  grid: Grid2X2,
  list: List,
  bell: Bell,
  help: CircleHelp,
  plus: Plus,
  more: MoreHorizontal,
  refresh: RefreshCw,
  pause: Pause,
  warning: TriangleAlert,
  check: Check,
  git: GitBranch,
}

export function Icon({ name }: { name: IconName }) {
  const Lucide = icons[name]

  return <Lucide className="icon" aria-hidden="true" strokeWidth={2} />
}
