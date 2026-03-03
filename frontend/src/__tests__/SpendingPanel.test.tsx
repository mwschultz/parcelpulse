import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import SpendingPanel, { SpendingData } from '../components/SpendingPanel';

vi.mock('react-chartjs-2', () => ({ Bar: () => null }));

function makeData(overrides: Partial<SpendingData> = {}): SpendingData {
  return {
    bracket: '50000_69999',
    bracket_label: '$50,000\u2013$69,999',
    households: 1200,
    categories: [
      { key: 'food_at_home', label: 'Food at Home', per_unit: 5000, total: 6000000 },
      { key: 'transportation', label: 'Transportation', per_unit: 9000, total: 10800000 },
    ],
    is_estimated: false,
    ...overrides,
  };
}

describe('SpendingPanel', () => {
  it('renders_nothing_when_data_null', () => {
    const { container } = render(<SpendingPanel data={null} loading={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows_loading_skeleton', () => {
    const { container } = render(<SpendingPanel data={null} loading={true} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders_bracket_label', () => {
    render(<SpendingPanel data={makeData()} loading={false} />);
    expect(screen.getByText('$50,000\u2013$69,999')).toBeInTheDocument();
  });

  it('renders_household_count', () => {
    render(<SpendingPanel data={makeData({ households: 1200 })} loading={false} />);
    expect(screen.getByText('1,200')).toBeInTheDocument();
  });

  it('shows_estimated_banner_when_is_estimated', () => {
    render(<SpendingPanel data={makeData({ is_estimated: true })} loading={false} />);
    expect(screen.getByText(/Income data unavailable/)).toBeInTheDocument();
  });

  it('does_not_show_banner_when_not_estimated', () => {
    render(<SpendingPanel data={makeData({ is_estimated: false })} loading={false} />);
    expect(screen.queryByText(/Income data unavailable/)).not.toBeInTheDocument();
  });
});
