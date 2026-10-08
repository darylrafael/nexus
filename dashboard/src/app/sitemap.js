export default function sitemap() {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://nexus.local';

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'hourly',
      priority: 1.0,
    },
  ];
}
