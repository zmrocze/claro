import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  client: '@hey-api/client-fetch',
  input: 'http://localhost:8000/openapi.json',
  output: 'src/api-client',
  plugins: [
    {
      name: '@hey-api/typescript'
    },
    {
      name: '@hey-api/sdk'
    }
  ]
});
