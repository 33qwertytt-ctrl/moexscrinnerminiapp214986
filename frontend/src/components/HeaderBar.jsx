export default function HeaderBar({ search, onSearchChange, onOpenFilters }) {
  return (
    <header className="app-header">
      <div className="header-row">
        <input
          type="search"
          className="search-input"
          placeholder="Поиск по тикеру, названию или компании"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          enterKeyHint="search"
        />
        <button type="button" className="icon-btn tap-scale" onClick={onOpenFilters} aria-label="Фильтры">
          <span className="icon-filter" />
        </button>
      </div>
    </header>
  );
}
