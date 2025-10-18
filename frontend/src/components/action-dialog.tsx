/**
 * Action Confirmation Dialog
 * Shows pending actions and allows user to confirm or cancel them
 */

import type { ActionConfirmation } from '@/api-client'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface ActionDialogProps {
  action: ActionConfirmation | null
  open: boolean
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

/**
 * Format action parameters for display
 */
function formatParameters(params: Record<string, unknown>): string {
  if (!params || Object.keys(params).length === 0) {
    return 'None'
  }

  return Object.entries(params)
    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
    .join('\n')
}

/**
 * Get human-readable action type label
 */
function getActionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    mock: 'Mock Action',
    reminder: 'Set Reminder',
    note: 'Save Note',
    search: 'Search',
  }
  return labels[type] || type
}

export function ActionDialog({
  action,
  open,
  onConfirm,
  onCancel,
  isLoading = false,
}: ActionDialogProps) {
  if (!action) return null

  return (
    <Dialog open={open} onOpenChange={open => !open && onCancel()}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>Confirm Action</DialogTitle>
          <DialogDescription>
            The assistant wants to perform the following action. Please review and
            confirm or cancel.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Action Type */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-slate-700">Action Type</h4>
            <p className="rounded-md bg-slate-100 px-3 py-2 text-sm">
              {getActionTypeLabel(action.action_type)}
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-slate-700">Description</h4>
            <p className="rounded-md bg-slate-100 px-3 py-2 text-sm">
              {action.description}
            </p>
          </div>

          {/* Parameters */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-slate-700">Parameters</h4>
            <pre className="whitespace-pre-wrap rounded-md bg-slate-100 px-3 py-2 text-xs font-mono">
              {formatParameters(action.parameters)}
            </pre>
          </div>

          {/* Expiry Info */}
          <div className="text-xs text-slate-500">
            This action will expire at{' '}
            {new Date(action.expires_at).toLocaleTimeString()}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? 'Confirming...' : 'Confirm'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
