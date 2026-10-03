import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
import eventflowAiPlugin from '@internal/backstage-plugin-eventflow-ai';
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';

export default createApp({
  features: [catalogPlugin, navModule, homeModule, eventflowAiPlugin],
});
