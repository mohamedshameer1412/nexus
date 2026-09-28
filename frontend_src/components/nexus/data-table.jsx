"use client";
// A data table for every list of records: search, sort, filter, show/hide columns, paging, and export (CSV, Excel, PDF, print).
import { useMemo, useState } from "react";
import {
  flexRender, getCoreRowModel, getFilteredRowModel, getPaginationRowModel, getSortedRowModel, useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown, ChevronLeft, ChevronRight, Columns3, Download, FileSpreadsheet, FileText, Printer, Search, Sheet as SheetIcon } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
  Button, Checkbox, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
  Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/primitives";

const text = (v) => (v == null ? "" : typeof v === "boolean" ? (v ? "yes" : "no") : String(v));

/** The visible columns as plain values, in order, for export. Uses each column's `meta.export(row)` when given. */
function exportRows(table) {
  const cols = table.getVisibleLeafColumns().filter((c) => c.columnDef.meta?.export !== false && c.id !== "select");
  const header = cols.map((c) => c.columnDef.meta?.label ?? (typeof c.columnDef.header === "string" ? c.columnDef.header : c.id));
  const rows = table.getPrePaginationRowModel().rows.map((r) => cols.map((c) => {
    const f = c.columnDef.meta?.export;
    return typeof f === "function" ? f(r.original) : r.getValue(c.id);
  }));
  return { header, rows };
}

function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}

async function exportAs(kind, table, filename, title) {
  const { header, rows } = exportRows(table);
  const stamp = new Date().toISOString().slice(0, 10);
  const base = `${filename}-${stamp}`;
  if (kind === "csv") {
    const esc = (v) => { const s = text(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const csv = "﻿" + [header, ...rows].map((r) => r.map(esc).join(",")).join("\n");
    return download(new Blob([csv], { type: "text/csv;charset=utf-8" }), `${base}.csv`);
  }
  if (kind === "xlsx") {
    const ExcelJS = (await import("exceljs")).default;
    const wb = new ExcelJS.Workbook();
    wb.creator = "Nexus";
    const ws = wb.addWorksheet((title || "Data").slice(0, 31), { views: [{ state: "frozen", ySplit: 1 }] });
    ws.addRow(header);
    rows.forEach((r) => ws.addRow(r.map((v) => (v == null ? null : v))));
    ws.getRow(1).eachCell((c) => { c.font = { bold: true, color: { argb: "FFFFFFFF" } }; c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0194E2" } }; });
    ws.columns.forEach((col, i) => { col.width = Math.min(60, Math.max(10, ...[header[i], ...rows.slice(0, 300).map((r) => r[i])].map((v) => text(v).length + 2))); });
    ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: header.length } };
    const buf = await wb.xlsx.writeBuffer();
    return download(new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${base}.xlsx`);
  }
  if (kind === "pdf") {
    const { jsPDF } = await import("jspdf");
    const autoTable = (await import("jspdf-autotable")).default;
    const doc = new jsPDF({ orientation: header.length > 6 ? "landscape" : "portrait", unit: "pt" });
    const w = doc.internal.pageSize.getWidth();
    doc.setFillColor(1, 148, 226); doc.rect(0, 0, w, 46, "F");
    doc.setTextColor(255); doc.setFont("helvetica", "bold"); doc.setFontSize(14); doc.text("NEXUS", 28, 29);
    doc.setFont("helvetica", "normal"); doc.setFontSize(10); doc.text(title || filename, w - 28, 29, { align: "right" });
    doc.setTextColor(82, 102, 125); doc.setFontSize(9); doc.text(`${rows.length} rows · exported ${new Date().toLocaleString()}`, 28, 66);
    autoTable(doc, {
      head: [header], body: rows.map((r) => r.map(text)), startY: 76, margin: { left: 28, right: 28 },
      styles: { fontSize: 8, cellPadding: 4, textColor: [11, 34, 57], lineColor: [213, 232, 245], lineWidth: 0.4 },
      headStyles: { fillColor: [1, 148, 226], textColor: 255, fontStyle: "bold" }, alternateRowStyles: { fillColor: [242, 248, 252] },
      didDrawPage: () => { doc.setFontSize(8); doc.setTextColor(82, 102, 125); doc.text(`Page ${doc.getNumberOfPages()}`, w - 28, doc.internal.pageSize.getHeight() - 16, { align: "right" }); },
    });
    return doc.save(`${base}.pdf`);
  }
}

function SortIcon({ dir }) {
  if (dir === "asc") return <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />;
  if (dir === "desc") return <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />;
  return <ChevronsUpDown className="h-3.5 w-3.5 opacity-40" aria-hidden="true" />;
}

/**
 * columns: TanStack column defs. Put a plain label in meta.label when `header` is not a string; meta.align = "right" for numbers;
 * meta.export = function(row) for the exported value, or false to leave the column out of exports.
 * facets: [{ id, label, options?: [{value,label}] }] adds a filter select per column (options default to the distinct values).
 * serverExports: [{ label, href, icon }] adds server-built files (ReportLab PDF, formatted workbook) to the export menu.
 */
export function DataTable({ columns, data, filename = "nexus-export", title, searchPlaceholder = "Search…", pageSize = 10, onRowClick, facets = [],
  serverExports = [], initialSort = [], empty = "No rows yet.", toolbar, dense, hidden = {}, className }) {
  const [sorting, setSorting] = useState(initialSort);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnFilters, setColumnFilters] = useState([]);
  const [columnVisibility, setColumnVisibility] = useState(hidden);
  const [busy, setBusy] = useState(null);
  const cols = useMemo(() => columns.map((c) => (facets.some((f) => f.id === (c.id ?? c.accessorKey)) && !c.filterFn ? { ...c, filterFn: "equalsString" } : c)), [columns, facets]);
  const table = useReactTable({
    data: data ?? [], columns: cols, state: { sorting, globalFilter, columnFilters, columnVisibility },
    onSortingChange: setSorting, onGlobalFilterChange: setGlobalFilter, onColumnFiltersChange: setColumnFilters, onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getFilteredRowModel: getFilteredRowModel(), getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } }, globalFilterFn: "includesString",
  });
  const facetOptions = useMemo(() => Object.fromEntries(facets.map((f) => [f.id, f.options ?? [...new Set((data ?? []).map((r) => r[f.id]).filter((v) => v != null && v !== ""))].sort().map((v) => ({ value: String(v), label: String(v) }))])), [facets, data]);
  const run = async (kind) => {
    setBusy(kind);
    try { await exportAs(kind, table, filename, title); toast.success(`Exported ${kind.toUpperCase()}`); }
    catch (e) { console.error(e); toast.error("The export failed. Try again."); }
    finally { setBusy(null); }
  };
  const total = table.getFilteredRowModel().rows.length;
  const { pageIndex, pageSize: size } = table.getState().pagination;

  return (
    <div className={cn("rounded-xl border border-border/80 bg-surface shadow-card", className)}>
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-3 sm:px-4">
        <div className="relative min-w-[12rem] flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
          <Input value={globalFilter} onChange={(e) => { setGlobalFilter(e.target.value); table.setPageIndex(0); }} placeholder={searchPlaceholder} aria-label="Search the table" className="h-9 pl-9 text-sm" />
        </div>
        {facets.map((f) => (
          <Select key={f.id} value={String(table.getColumn(f.id)?.getFilterValue() ?? "__all")} onValueChange={(v) => { table.getColumn(f.id)?.setFilterValue(v === "__all" ? undefined : v); table.setPageIndex(0); }}>
            <SelectTrigger className="h-9 w-auto min-w-[8.5rem] text-sm" aria-label={f.label}><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all">All {f.label.toLowerCase()}</SelectItem>
              {facetOptions[f.id].map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        ))}
        {toolbar}
        <div className="ml-auto flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="secondary" size="sm"><Columns3 className="h-4 w-4" />Columns</Button></DropdownMenuTrigger>
            <DropdownMenuContent className="max-h-80 overflow-y-auto">
              <DropdownMenuLabel>Show columns</DropdownMenuLabel>
              {table.getAllLeafColumns().filter((c) => c.getCanHide()).map((c) => (
                <DropdownMenuItem key={c.id} onSelect={(e) => { e.preventDefault(); c.toggleVisibility(); }}>
                  <Checkbox checked={c.getIsVisible()} aria-hidden="true" tabIndex={-1} className="pointer-events-none" />
                  {c.columnDef.meta?.label ?? (typeof c.columnDef.header === "string" ? c.columnDef.header : c.id)}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button size="sm" loading={!!busy}><Download className="h-4 w-4" />Export</Button></DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>{total} row{total === 1 ? "" : "s"}, visible columns</DropdownMenuLabel>
              <DropdownMenuItem onSelect={() => run("csv")}><FileText />CSV</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => run("xlsx")}><FileSpreadsheet />Excel (.xlsx)</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => run("pdf")}><SheetIcon />PDF table</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => window.print()}><Printer />Print</DropdownMenuItem>
              {serverExports.length > 0 && <><DropdownMenuSeparator /><DropdownMenuLabel>Formatted reports</DropdownMenuLabel></>}
              {serverExports.map((s) => (
                <DropdownMenuItem key={s.href} asChild><a href={s.href} download className="no-underline text-inherit">{s.icon ? <s.icon /> : <Download />}{s.label}</a></DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <div className="nx-scroll-light overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="bg-surface-2">
                {hg.headers.map((h) => {
                  const sortable = h.column.getCanSort();
                  const align = h.column.columnDef.meta?.align;
                  return (
                    <th key={h.id} scope="col" aria-sort={h.column.getIsSorted() === "asc" ? "ascending" : h.column.getIsSorted() === "desc" ? "descending" : undefined}
                      className={cn("whitespace-nowrap border-b border-border px-3 py-2.5 text-left text-[12.5px] font-semibold text-muted first:pl-4 last:pr-4", align === "right" && "text-right")}>
                      {h.isPlaceholder ? null : sortable ? (
                        <button type="button" onClick={h.column.getToggleSortingHandler()} className={cn("inline-flex items-center gap-1 hover:text-foreground", align === "right" && "flex-row-reverse")}>
                          {flexRender(h.column.columnDef.header, h.getContext())}<SortIcon dir={h.column.getIsSorted()} />
                        </button>
                      ) : flexRender(h.column.columnDef.header, h.getContext())}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 && (
              <tr><td colSpan={table.getVisibleLeafColumns().length} className="px-4 py-10 text-center text-sm text-muted">{globalFilter || columnFilters.length ? "No rows match the search or filters." : empty}</td></tr>
            )}
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                className={cn("border-b border-border/70 last:border-0 transition-colors", onRowClick && "cursor-pointer hover:bg-brand-wash")}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className={cn("px-3 align-middle first:pl-4 last:pr-4", dense ? "py-1.5" : "py-2.5", cell.column.columnDef.meta?.align === "right" && "tabular text-right")}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-3 py-2.5 text-[13px] text-muted sm:px-4">
        <span className="tabular">{total ? `${pageIndex * size + 1}–${Math.min(total, (pageIndex + 1) * size)} of ${total}` : "0 rows"}</span>
        <div className="flex items-center gap-2">
          <Select value={String(size)} onValueChange={(v) => table.setPageSize(Number(v))}>
            <SelectTrigger className="h-8 w-[7.5rem] text-[13px]" aria-label="Rows per page"><SelectValue /></SelectTrigger>
            <SelectContent>{[...new Set([5, 10, 25, 50, 100, size])].sort((a, b) => a - b).map((n) => <SelectItem key={n} value={String(n)}>{n} per page</SelectItem>)}</SelectContent>
          </Select>
          <Button variant="secondary" size="icon-sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></Button>
          <Button variant="secondary" size="icon-sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()} aria-label="Next page"><ChevronRight className="h-4 w-4" /></Button>
        </div>
      </div>
    </div>
  );
}

/** A small inline bar for a 0..100 value inside a table cell. */
export function CellBar({ value, tone = "brand" }) {
  if (value == null) return <span className="text-muted">–</span>;
  const color = { brand: "bg-brand", strong: "bg-strong", mid: "bg-mid", weak: "bg-weak" }[tone];
  return (
    <span className="inline-flex items-center gap-2">
      <span className="tabular w-10 text-right">{Math.round(value)}%</span>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-brand-soft/70"><span className={cn("block h-full rounded-full", color)} style={{ width: `${Math.max(2, Math.min(100, value))}%` }} /></span>
    </span>
  );
}
