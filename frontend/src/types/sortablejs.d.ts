declare module 'sortablejs' {
  export interface SortableEvent {
    oldIndex?: number
    newIndex?: number
  }

  export interface SortableOptions {
    animation?: number
    handle?: string
    draggable?: string
    forceFallback?: boolean
    fallbackOnBody?: boolean
    fallbackTolerance?: number
    ghostClass?: string
    chosenClass?: string
    dragClass?: string
    onEnd?: (event: SortableEvent) => void
  }

  export default class Sortable {
    constructor(element: HTMLElement, options?: SortableOptions)
    destroy(): void
    option(name: string, value: unknown): void
  }
}
