import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import EvacuNetAlert from './EvacuNetAlert';

describe('EvacuNetAlert', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('stays hidden when inactive', () => {
    render(<EvacuNetAlert active={false} />);

    expect(screen.queryByText('EMERGENCY EVACUATION')).not.toBeInTheDocument();
  });

  it('shows elapsed evacuation time while active', () => {
    render(<EvacuNetAlert active hazardScore={0.91} affectedZones={['North']} />);

    expect(screen.getByText('EMERGENCY EVACUATION')).toBeInTheDocument();
    expect(screen.getByText('00:00')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2_000);
    });

    expect(screen.getByText('00:02')).toBeInTheDocument();
    expect(screen.getByText('91%')).toBeInTheDocument();
    expect(screen.getByText('North')).toBeInTheDocument();
  });
});
