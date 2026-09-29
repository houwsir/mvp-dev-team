interface PaginationProps {
  page: number
  pageSize: 20 | 50
  total: number
  totalPages: number
  disabled?: boolean
  onPageChange: (page: number) => void
  onPageSizeChange: (size: 20 | 50) => void
}

export function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  disabled,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  return (
    <div className="pagination" aria-label="分页">
      <span>共 {total} 条</span>
      <button
        className="button secondary compact"
        disabled={disabled || page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        上一页
      </button>
      <span className="page-number">
        {totalPages === 0 ? 0 : page} / {totalPages}
      </span>
      <button
        className="button secondary compact"
        disabled={disabled || totalPages === 0 || page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        下一页
      </button>
      <select
        value={pageSize}
        disabled={disabled}
        aria-label="每页条数"
        onChange={(event) => onPageSizeChange(Number(event.target.value) as 20 | 50)}
      >
        <option value={20}>20 条/页</option>
        <option value={50}>50 条/页</option>
      </select>
    </div>
  )
}
