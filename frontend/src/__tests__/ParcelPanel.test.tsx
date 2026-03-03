import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ParcelPanel, { ParcelsData, ParcelData } from '../components/ParcelPanel';

function makeParcel(overrides: Partial<ParcelData> = {}): ParcelData {
  return {
    parno: 'P001',
    address: '100 Test St',
    city: 'Raleigh',
    owner: 'Test Owner',
    owner_type: '',
    land_value: 100000,
    improvement_value: 200000,
    total_value: 300000,
    use_description: 'Commercial',
    acres: 0.5,
    has_structure: true,
    year_built: 2000,
    sale_date: null,
    distance_mi: 0.1,
    geometry: null,
    ...overrides,
  };
}

const defaultProps = {
  loading: false,
  activeParcelId: null,
  selectedParcelId: null,
  onHover: vi.fn(),
  onSelect: vi.fn(),
};

describe('ParcelPanel', () => {
  it('renders_nothing_when_data_null', () => {
    const { container } = render(<ParcelPanel data={null} {...defaultProps} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows_loading_skeleton', () => {
    const { container } = render(<ParcelPanel data={null} {...defaultProps} loading={true} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows_non_nc_fallback_banner', () => {
    const data: ParcelsData = {
      coverage: false,
      state: 'TX',
      message: null,
      parcels: [],
      rate_limited: false,
    };
    render(<ParcelPanel data={data} {...defaultProps} />);
    expect(screen.getByText(/North Carolina/)).toBeInTheDocument();
  });

  it('shows_rate_limited_message', () => {
    const data: ParcelsData = {
      coverage: true,
      state: 'NC',
      message: null,
      parcels: [],
      rate_limited: true,
    };
    render(<ParcelPanel data={data} {...defaultProps} />);
    expect(screen.getByText(/Daily request limit/)).toBeInTheDocument();
  });

  it('shows_empty_parcels_message', () => {
    const data: ParcelsData = {
      coverage: true,
      state: 'NC',
      message: null,
      parcels: [],
      rate_limited: false,
    };
    render(<ParcelPanel data={data} {...defaultProps} />);
    expect(screen.getByText(/No parcels found/)).toBeInTheDocument();
  });

  it('renders_parcel_cards_with_addresses', () => {
    const data: ParcelsData = {
      coverage: true,
      state: 'NC',
      message: null,
      parcels: [
        makeParcel({ parno: 'P001', address: '100 First Ave' }),
        makeParcel({ parno: 'P002', address: '200 Second Ave' }),
      ],
      rate_limited: false,
    };
    render(<ParcelPanel data={data} {...defaultProps} />);
    expect(screen.getByText('100 First Ave')).toBeInTheDocument();
    expect(screen.getByText('200 Second Ave')).toBeInTheDocument();
  });

  it('calls_onHover_on_mouse_enter', () => {
    const onHover = vi.fn();
    const data: ParcelsData = {
      coverage: true,
      state: 'NC',
      message: null,
      parcels: [makeParcel({ parno: 'P001', address: '100 First Ave' })],
      rate_limited: false,
    };
    render(<ParcelPanel data={data} {...defaultProps} onHover={onHover} />);
    const card = screen.getByText('100 First Ave').closest('.rounded-lg')!;
    fireEvent.mouseEnter(card);
    expect(onHover).toHaveBeenCalledWith('P001');
  });

  it('calls_onSelect_on_click', () => {
    const onSelect = vi.fn();
    const data: ParcelsData = {
      coverage: true,
      state: 'NC',
      message: null,
      parcels: [makeParcel({ parno: 'P001', address: '100 First Ave' })],
      rate_limited: false,
    };
    render(<ParcelPanel data={data} {...defaultProps} onSelect={onSelect} />);
    const card = screen.getByText('100 First Ave').closest('.rounded-lg')!;
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledWith('P001');
  });
});
