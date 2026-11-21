'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type OnChangeFn,
  type PaginationState,
  type SortingState,
  type VisibilityState,
} from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Columns3, Search, X } from 'lucide-react';
import { apiExportCsv, ApiError, useTableData, type QueryParamValue } from '@/lib/api';
import { useDrilldown } from './DrilldownDrawer';
import { useFilters } from '@/lib/filters';
import { formatCell, inferColumnType, statusTone } from '@/lib/format';
import type { ColumnType, FilterState, TableColumn, TableRow } from '@/lib/types';
import { cn, displayValue } from '@/lib/utils';
import { Badge, Card, CardHeader, EmptyState, ErrorState, Skeleton, Spinner } from './ui';

const EXPORT_LIMIT = 5000;

interface DataTableProps {
  endpoint?: string;
  columns: TableColumn[];
  filters: FilterState;
  /** Page-scoped filter values forwarded to the API. */
  params?: Record<string, QueryParamValue>;
  title?: string;
  searchable?: boolean;
  pageSize?: number;
  exportName?: string;
  initialSearch?: string;
  /** Optional custom row interaction; defaults to the shared drill-down drawer. */
  onRowClick?: (row: TableRow) => void;
  /** Only one table per page should respond to the global Export action. */
  primaryExport?: boolean;
}

function resolveColumns(configured: TableColumn[], rows: TableRow[]): TableColumn[] {
  const first = rows[0] || {};
  const keys = Object.keys(first);
  if (!keys.length) return configured.filter((column) => !column.hidden);
  const matches = configured.filter((column) => keys.includes(column.key) && !column.hidden);
  if (matches.length >= Math.min(2, keys.length)) return matches;
  return keys.slice(0, 12).map((key) => ({
    key,
    title: key.replace(/[_-]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
    type: inferColumnType(key, first[key]) as ColumnType,
    sortable: true,
  }));
}

export function DataTable({ endpoint, columns, filters, params: extraParams, title = 'Detailed records', searchable = true, pageSize = 25, exportName = 'export', initialSearch = '', onRowClick, primaryExport = true }: DataTableProps) {
  const { openDrilldown } = useDrilldown();
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize });
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [searchInput, setSearchInput] = useState(initialSearch);
  const [search, setSearch] = useState(initialSearch);
  const [showColumns, setShowColumns] = useState(false);
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPagination((current) => ({ ...current, pageIndex: 0 }));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const params = useMemo<Record<string, QueryParamValue>>(
    () => ({
      ...extraParams,
      page: pagination.pageIndex + 1,
      page_size: pagination.pageSize,
      search: search || undefined,
      sort_by: sorting[0]?.id,
      sort_dir: sorting[0] ? (sorting[0].desc ? 'desc' : 'asc') : undefined,
    }),
    [extraParams, pagination.pageIndex, pagination.pageSize, search, sorting],
  );
  const query = useTableData(endpoint, filters, params, Boolean(endpoint));
  const rows = useMemo(() => (Array.isArray(query.data?.data) ? query.data.data : []), [query.data]);
  const paginationMeta = query.data?.pagination;
  const totalRecords = paginationMeta?.total_records ?? rows.length;
  const pageCount = Math.max(1, paginationMeta?.total_pages ?? Math.ceil(totalRecords / pagination.pageSize));

  const resolved = useMemo(() => resolveColumns(columns, rows), [columns, rows]);

  const exportCsv = useCallback(async () => {
    if (!endpoint) return;
    setExportError('');
    try {
      await apiExportCsv(
        endpoint,
        filters,
        {
          ...extraParams,
          page: 1,
          page_size: EXPORT_LIMIT,
          search: search || undefined,
          sort_by: sorting[0]?.id,
          sort_dir: sorting[0] ? (sorting[0].desc ? 'desc' : 'asc') : undefined,
        },
        `${exportName}-filtered`,
      );
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Unable to export rows.';
      setExportError(message);
      console.error('Export failed', error);
    }
  }, [endpoint, filters, extraParams, search, sorting, exportName]);

  useEffect(() => {
    if (!primaryExport) return;
    window.addEventListener('hospital360:export', exportCsv);
    return () => window.removeEventListener('hospital360:export', exportCsv);
  }, [exportCsv, primaryExport]);

  const handleSortingChange: OnChangeFn<SortingState> = (updater) => {
    setSorting(updater);
    setPagination((current) => ({ ...current, pageIndex: 0 }));
  };

  const tableColumns = useMemo<ColumnDef<TableRow, unknown>[]>(
    () =>
      resolved.map((column) => ({
        accessorKey: column.key,
        header: ({ column: tableColumn }) => (
          <button
            type="button"
            onClick={tableColumn.getToggleSortingHandler()}
            className="flex items-center gap-1 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500 hover:text-teal"
          >
            {column.title}
            {tableColumn.getIsSorted() === 'asc' ? <ArrowUp className="h-3 w-3" /> : tableColumn.getIsSorted() === 'desc' ? <ArrowDown className="h-3 w-3" /> : null}
          </button>
        ),
        cell: ({ getValue }) => {
          const value = getValue();
          if (column.type === 'badge' || /status|severity|resolution/.test(column.key)) {
            return <Badge tone={statusTone(value)}>{displayValue(value)}</Badge>;
          }
          return <span className="whitespace-nowrap text-xs text-ink">{formatCell(value, column.type)}</span>;
        },
        enableSorting: column.sortable !== false,
      })),
    [resolved],
  );

  const table = useReactTable({
    data: rows,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    pageCount,
    state: { pagination, sorting, columnVisibility },
    onPaginationChange: setPagination,
    onSortingChange: handleSortingChange,
    onColumnVisibilityChange: setColumnVisibility,
    getRowId: (row, index) => String(row[resolved[0]?.key || ''] ?? index),
  });

  return (
    <Card className="overflow-hidden">
      <CardHeader
        title={title}
        subtitle={exportError ? `Export failed: ${exportError}` : `${totalRecords.toLocaleString('en-US')} records${search ? ` · search: ${search}` : ''}`}
        action={
          <div className="flex items-center gap-2">
            {query.isFetching && <Spinner className="text-teal" />}
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex h-7 items-center gap-1.5 rounded border border-line px-2 text-[11px] font-medium text-slate-600 hover:border-teal hover:text-teal"
            >
              Export CSV
            </button>
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowColumns((value) => !value)}
                className="inline-flex h-7 items-center gap-1.5 rounded border border-line px-2 text-[11px] font-medium text-slate-600 hover:border-teal hover:text-teal"
              >
                <Columns3 className="h-3.5 w-3.5" /> Columns
              </button>
              {showColumns && (
                <div className="absolute right-0 top-8 z-30 max-h-64 w-48 overflow-auto rounded-lg border border-line bg-white p-2 shadow-lg">
                  {table.getAllLeafColumns().map((column) => (
                    <label key={column.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-xs text-ink hover:bg-canvas">
                      <input type="checkbox" checked={column.getIsVisible()} onChange={column.getToggleVisibilityHandler()} className="accent-teal" />
                      <span className="truncate">{resolved.find((item) => item.key === column.id)?.title || column.id}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
        }
      />
      {searchable && (
        <div className="border-b border-line px-5 py-3">
          <div className="relative max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search records…"
              aria-label="Search records"
              className="h-9 w-full rounded-md border border-line bg-white pl-8 pr-8 text-xs outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
            />
            {searchInput && (
              <button type="button" onClick={() => setSearchInput('')} className="absolute right-2 top-2.5 text-slate-400 hover:text-ink" aria-label="Clear search">
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {query.isLoading ? (
        <div className="space-y-2 p-5">{Array.from({ length: 6 }).map((_item, index) => <Skeleton key={index} className="h-7 w-full" />)}</div>
      ) : query.isError ? (
        <ErrorState message={query.error?.message || 'Unable to load records.'} onRetry={() => query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message="No records found" hint="Try widening the date range or clearing filters." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead className="bg-canvas">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="whitespace-nowrap px-4 py-2.5">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-line">
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} onClick={() => onRowClick ? onRowClick(row.original) : openDrilldown(row.original, 'Record details')} className="cursor-pointer transition hover:bg-teal-light/40">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className={cn('whitespace-nowrap px-4 py-2.5')}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
        <p className="text-[11px] text-slate-500">
          {totalRecords ? `${pagination.pageIndex * pagination.pageSize + 1}–${Math.min((pagination.pageIndex + 1) * pagination.pageSize, totalRecords)} of ${totalRecords}` : '0 records'}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="inline-flex h-7 items-center gap-1 rounded border border-line px-2 text-[11px] text-slate-600 disabled:opacity-40"
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Previous
          </button>
          <span className="text-[11px] text-slate-500">Page {pagination.pageIndex + 1} of {pageCount}</span>
          <button
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="inline-flex h-7 items-center gap-1 rounded border border-line px-2 text-[11px] text-slate-600 disabled:opacity-40"
          >
            Next <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </Card>
  );
}
