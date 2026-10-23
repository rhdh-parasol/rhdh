import { renderWithEffects } from '@backstage/test-utils';

jest.setTimeout(30_000);

describe('App', () => {
  let app: typeof import('./App').default;

  // Loading the full frontend is setup, not part of the render assertion.
  beforeAll(async () => {
    process.env = {
      NODE_ENV: 'test',
      APP_CONFIG: [
        {
          data: {
            app: {
              title: 'Test',
              support: { url: 'http://localhost:7007/support' },
            },
            backend: { baseUrl: 'http://localhost:7007' },
            lighthouse: {
              baseUrl: 'http://localhost:3003',
            },
            techdocs: {
              storageUrl: 'http://localhost:7007/api/techdocs/static/docs',
            },
          },
          context: 'test',
        },
      ] as any,
    };

    ({ default: app } = await import('./App'));
  }, 60_000);

  it('should render', async () => {
    const rendered = await renderWithEffects(app);
    expect(rendered.baseElement).toBeInTheDocument();
  });
});
