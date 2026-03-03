import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CompetitorsPanel, { CompetitorData } from '../components/CompetitorsPanel';

function makeData(overrides: Partial<CompetitorData> = {}): CompetitorData {
  return {
    items: [],
    categories: [
      { key: 'grocery', label: 'Grocery', color: '#22c55e', count: 3 },
      { key: 'restaurant', label: 'Restaurant', color: '#f97316', count: 5 },
    ],
    density_score: 'Medium',
    radius_m: 1609,
    ...overrides,
  };
}

describe('CompetitorsPanel', () => {
  it('renders_nothing_when_data_null', () => {
    const { container } = render(
      <CompetitorsPanel data={null} loading={false} visibleCategories={new Set()} onToggle={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('shows_loading_skeleton', () => {
    const { container } = render(
      <CompetitorsPanel data={null} loading={true} visibleCategories={new Set()} onToggle={vi.fn()} />
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders_density_badge_text', () => {
    render(
      <CompetitorsPanel data={makeData({ density_score: 'High' })} loading={false}
        visibleCategories={new Set(['grocery'])} onToggle={vi.fn()} />
    );
    expect(screen.getByText(/High Density/)).toBeInTheDocument();
  });

  it('renders_category_rows_with_counts', () => {
    render(
      <CompetitorsPanel data={makeData()} loading={false}
        visibleCategories={new Set(['grocery', 'restaurant'])} onToggle={vi.fn()} />
    );
    expect(screen.getByText('Grocery')).toBeInTheDocument();
    expect(screen.getByText('Restaurant')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('toggle_calls_onToggle_with_key', () => {
    const onToggle = vi.fn();
    render(
      <CompetitorsPanel data={makeData()} loading={false}
        visibleCategories={new Set(['grocery', 'restaurant'])} onToggle={onToggle} />
    );
    const groceryBtn = screen.getByText('Grocery').closest('button')!;
    fireEvent.click(groceryBtn);
    expect(onToggle).toHaveBeenCalledWith('grocery');
  });

  it('hidden_category_has_reduced_opacity', () => {
    render(
      <CompetitorsPanel data={makeData()} loading={false}
        visibleCategories={new Set(['restaurant'])} onToggle={vi.fn()} />
    );
    const groceryBtn = screen.getByText('Grocery').closest('button')!;
    expect(groceryBtn).toHaveStyle({ opacity: '0.4' });
  });
});
