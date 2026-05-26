import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import CrowdsourcedFeed from './CrowdsourcedFeed';

describe('CrowdsourcedFeed', () => {
  it('submits local reports without mutating external data', async () => {
    const user = userEvent.setup();
    render(<CrowdsourcedFeed />);

    await user.type(
      screen.getByPlaceholderText('Submit a field report…'),
      'Queue building at Gate C',
    );
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(screen.getByText('Queue building at Gate C')).toBeInTheDocument();
    expect(screen.getByText('6 messages')).toBeInTheDocument();
  });

  it('renders external messages as the source of truth', () => {
    render(
      <CrowdsourcedFeed
        messages={[
          {
            id: 'external-1',
            type: 'ALERT',
            sender: 'Control',
            text: 'Use Gate E',
            timestamp: new Date('2026-05-27T10:00:00+05:30').toISOString(),
          },
        ]}
      />,
    );

    expect(screen.getByText('Use Gate E')).toBeInTheDocument();
    expect(screen.getByText('1 messages')).toBeInTheDocument();
  });
});
