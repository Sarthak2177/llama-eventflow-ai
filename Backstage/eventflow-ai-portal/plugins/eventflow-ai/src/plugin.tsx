import {
  createFrontendPlugin,
  PageBlueprint,
} from '@backstage/frontend-plugin-api';

import { rootRouteRef } from './routes';

export const page = PageBlueprint.make({
  params: {
    path: '/eventflow-ai',
    routeRef: rootRouteRef,
    loader: () =>
      import('./components/ChatPage/ChatPage').then(m => (
        <m.ChatPage />
      )),
  },
});

export const eventflowAiPlugin = createFrontendPlugin({
  pluginId: 'eventflow-ai',
  extensions: [page],
  routes: {
    root: rootRouteRef,
  }
});
