import { Dialog, DialogContent, DialogTitle, DialogDescription } from "../../components/ui/dialog";
export const CatalogDialog = ({ title, children, onClose, busy = false, testId = "catalog-dialog" }) => (
  <Dialog open onOpenChange={open => { if (!open && !busy) onClose(); }}>
    <DialogContent data-testid={testId} className="!z-[210] max-h-[92vh] w-[calc(100%-24px)] max-w-3xl overflow-y-auto bg-white p-0" closeTestId={`${testId}-close`} closeDisabled={busy} overlayClassName="!z-[205]" onInteractOutside={e => { if (busy) e.preventDefault(); }} onEscapeKeyDown={e => { if (busy) e.preventDefault(); }}>
      <header className="border-b px-5 py-4"><DialogTitle data-testid={`${testId}-title`} className="text-lg">{title}</DialogTitle><DialogDescription className="sr-only">Pengelolaan katalog Kain Nusantara</DialogDescription></header>
      <div className="px-5 pb-5">{children}</div>
    </DialogContent>
  </Dialog>
);