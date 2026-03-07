import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import DemoPanel from '../components/DemoPanel';
import type { DemographicsData } from '../components/DemoPanel';

vi.mock('react-chartjs-2', () => ({ Bar: () => null }));

function makeData(overrides: Partial<DemographicsData> = {}): DemographicsData {
  return {
    population: 50000,
    median_age: 34.5,
    median_household_income: 75000,
    median_home_value: 320000,
    median_gross_rent: 1400,
    households: 20000,
    education: { hs_diploma: 5000, some_college: 4000, associates: 2000, bachelors: 8000, graduate: 3000 },
    race: { white: 35000, black: 7000, american_indian: 500, asian: 6000, pacific_islander: 1500 },
    fips: { level: 'block_group', state: '37', county: '183', tract: '052601', block_group: '1' },
    geography_level: 'block_group',
    geography_label: 'Block Group 1 · Tract 052601',
    boundary: null,
    ...overrides,
  };
}

describe('DemoPanel', () => {
  it('renders_nothing_when_data_null', () => {
    render(<DemoPanel data={null} loading={false} />);
    expect(screen.getByText(/Demographic data unavailable/)).toBeInTheDocument();
  });

  it('renders_population_formatted', () => {
    render(<DemoPanel data={makeData({ population: 50000 })} loading={false} />);
    expect(screen.getByText('50,000')).toBeInTheDocument();
  });

  it('renders_median_income_formatted', () => {
    render(<DemoPanel data={makeData({ median_household_income: 75000 })} loading={false} />);
    expect(screen.getByText('$75,000')).toBeInTheDocument();
  });

  it('renders_geography_label', () => {
    render(<DemoPanel data={makeData()} loading={false} />);
    expect(screen.getByText(/Block Group 1 · Tract 052601/)).toBeInTheDocument();
  });

  it('shows_fallback_banner_for_non_block_group', () => {
    render(<DemoPanel data={makeData({ geography_level: 'tract' })} loading={false} />);
    expect(screen.getByText(/Block group data unavailable/)).toBeInTheDocument();
  });
});
