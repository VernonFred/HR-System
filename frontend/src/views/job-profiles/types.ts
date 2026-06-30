export interface JobProfile {
  id: number
  name: string
  department?: string
  tags?: string[]
  dimensionCount?: number
  updatedAt: string
}

export interface Dimension {
  name: string
  weight: number
  description: string
}

export interface JobProfileForm {
  name: string
  department: string
  tags: string[]
  description: string
  dimensions: Dimension[]
}
