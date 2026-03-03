import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import SearchBar from '../components/SearchBar';

const MOCK_FEATURES = [
  {
    properties: {
      formatted: '4325 Glenwood Ave, Raleigh, NC 27612',
      lat: 35.83,
      lon: -78.66,
      state: 'North Carolina',
      state_code: 'NC',
      country_code: 'us',
    },
  },
  {
    properties: {
      formatted: '100 Main St, Durham, NC 27701',
      lat: 35.99,
      lon: -78.90,
      state: 'North Carolina',
      state_code: 'NC',
      country_code: 'us',
    },
  },
];

describe('SearchBar', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('renders_search_input', () => {
    render(<SearchBar onSelect={vi.fn()} />);
    expect(screen.getByPlaceholderText('Search an address...')).toBeInTheDocument();
  });

  it('does_not_fetch_for_short_input', async () => {
    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText('Search an address...');
    fireEvent.change(input, { target: { value: 'ab' } });
    await act(async () => { vi.advanceTimersByTime(400); });
    expect(fetch).not.toHaveBeenCalled();
  });

  it('fetches_after_3_chars_debounced', async () => {
    vi.mocked(fetch).mockResolvedValue({
      json: async () => ({ features: [] }),
    } as Response);

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText('Search an address...');
    fireEvent.change(input, { target: { value: 'abc' } });
    await act(async () => { vi.advanceTimersByTime(400); });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('shows_suggestions_from_response', async () => {
    vi.mocked(fetch).mockResolvedValue({
      json: async () => ({ features: MOCK_FEATURES }),
    } as Response);

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText('Search an address...');
    fireEvent.change(input, { target: { value: 'Ral' } });
    await act(async () => { await vi.runAllTimersAsync(); });

    expect(screen.getByText('4325 Glenwood Ave, Raleigh, NC 27612')).toBeInTheDocument();
    expect(screen.getByText('100 Main St, Durham, NC 27701')).toBeInTheDocument();
  });

  it('selects_suggestion_calls_onSelect', async () => {
    vi.mocked(fetch).mockResolvedValue({
      json: async () => ({ features: MOCK_FEATURES }),
    } as Response);

    const onSelect = vi.fn();
    render(<SearchBar onSelect={onSelect} />);
    const input = screen.getByPlaceholderText('Search an address...');
    fireEvent.change(input, { target: { value: 'Ral' } });
    await act(async () => { await vi.runAllTimersAsync(); });

    const item = screen.getByText('4325 Glenwood Ave, Raleigh, NC 27612');
    fireEvent.click(item);

    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledWith({
      address: '4325 Glenwood Ave, Raleigh, NC 27612',
      lat: 35.83,
      lng: -78.66,
      state: 'NC',
    });
  });

  it('clears_suggestions_after_selection', async () => {
    vi.mocked(fetch).mockResolvedValue({
      json: async () => ({ features: MOCK_FEATURES }),
    } as Response);

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText('Search an address...');
    fireEvent.change(input, { target: { value: 'Ral' } });
    await act(async () => { await vi.runAllTimersAsync(); });

    const item = screen.getByText('4325 Glenwood Ave, Raleigh, NC 27612');
    fireEvent.click(item);

    expect(screen.queryByText('100 Main St, Durham, NC 27701')).not.toBeInTheDocument();
  });
});
