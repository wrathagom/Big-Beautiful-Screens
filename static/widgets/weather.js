/**
 * Weather Widget - Current conditions and forecasts using Open-Meteo API
 *
 * Configuration options:
 * - location: City name (required) - geocoded automatically
 * - units: 'imperial' | 'metric' (default: 'imperial')
 * - display: 'current' | 'hourly' | 'daily' | 'full' (default: 'current')
 * - hours_to_show: number (default: 7) - for hourly view
 * - days_to_show: number (default: 7) - for daily view
 * - show_humidity: boolean (default: true)
 * - show_wind: boolean (default: true)
 * - show_precipitation: boolean (default: true)
 * - refresh_interval: number in ms (default: 1800000 = 30 min)
 */

import { registerWidget } from './registry.js';

// Cache for geocoding results to avoid repeated lookups
const geocodeCache = new Map();

// WMO Weather code to icon/description mapping
const WEATHER_CODES = {
    0: { icon: 'clear', description: 'Clear sky' },
    1: { icon: 'mostly-clear', description: 'Mainly clear' },
    2: { icon: 'partly-cloudy', description: 'Partly cloudy' },
    3: { icon: 'cloudy', description: 'Overcast' },
    45: { icon: 'fog', description: 'Fog' },
    48: { icon: 'fog', description: 'Depositing rime fog' },
    51: { icon: 'drizzle', description: 'Light drizzle' },
    53: { icon: 'drizzle', description: 'Moderate drizzle' },
    55: { icon: 'drizzle', description: 'Dense drizzle' },
    56: { icon: 'freezing-drizzle', description: 'Light freezing drizzle' },
    57: { icon: 'freezing-drizzle', description: 'Dense freezing drizzle' },
    61: { icon: 'rain', description: 'Slight rain' },
    63: { icon: 'rain', description: 'Moderate rain' },
    65: { icon: 'rain', description: 'Heavy rain' },
    66: { icon: 'freezing-rain', description: 'Light freezing rain' },
    67: { icon: 'freezing-rain', description: 'Heavy freezing rain' },
    71: { icon: 'snow', description: 'Slight snow' },
    73: { icon: 'snow', description: 'Moderate snow' },
    75: { icon: 'snow', description: 'Heavy snow' },
    77: { icon: 'snow', description: 'Snow grains' },
    80: { icon: 'showers', description: 'Slight rain showers' },
    81: { icon: 'showers', description: 'Moderate rain showers' },
    82: { icon: 'showers', description: 'Violent rain showers' },
    85: { icon: 'snow-showers', description: 'Slight snow showers' },
    86: { icon: 'snow-showers', description: 'Heavy snow showers' },
    95: { icon: 'thunderstorm', description: 'Thunderstorm' },
    96: { icon: 'thunderstorm', description: 'Thunderstorm with slight hail' },
    99: { icon: 'thunderstorm', description: 'Thunderstorm with heavy hail' }
};

// SVG icons for weather conditions
const WEATHER_ICONS = {
    'clear': `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></g></svg>`,
    'mostly-clear': `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="10" cy="10" r="4"/><g stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><line x1="10" y1="2" x2="10" y2="4"/><line x1="10" y1="16" x2="10" y2="18"/><line x1="3.76" y1="3.76" x2="5.17" y2="5.17"/><line x1="14.83" y1="14.83" x2="16.24" y2="16.24"/><line x1="2" y1="10" x2="4" y2="10"/><line x1="16" y1="10" x2="18" y2="10"/></g><path d="M16 18c0-2.21 1.79-4 4-4 0-3.31-2.69-6-6-6-.34 0-.68.03-1 .08" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.6"/></svg>`,
    'partly-cloudy': `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="9" r="4" opacity="0.8"/><path d="M18 18H8a4 4 0 0 1 0-8h.5a5.5 5.5 0 0 1 10.43 2.25A3 3 0 0 1 18 18z" fill="currentColor" opacity="0.9"/></svg>`,
    'cloudy': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20 18H6a4 4 0 0 1 0-8h.5a5.5 5.5 0 0 1 10.43 2.25A3 3 0 0 1 20 18z"/></svg>`,
    'fog': `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="8" x2="21" y2="8" opacity="0.4"/><line x1="5" y1="12" x2="19" y2="12" opacity="0.6"/><line x1="3" y1="16" x2="21" y2="16" opacity="0.8"/><line x1="7" y1="20" x2="17" y2="20"/></svg>`,
    'drizzle': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 14H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 14z" opacity="0.8"/><g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.6"><line x1="8" y1="17" x2="8" y2="19"/><line x1="12" y1="17" x2="12" y2="19"/><line x1="16" y1="17" x2="16" y2="19"/></g></svg>`,
    'freezing-drizzle': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 14H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 14z" opacity="0.8"/><g fill="currentColor" opacity="0.6"><circle cx="8" cy="18" r="1.5"/><circle cx="12" cy="18" r="1.5"/><circle cx="16" cy="18" r="1.5"/></g></svg>`,
    'rain': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 12H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 12z" opacity="0.8"/><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="7" y1="15" x2="7" y2="20"/><line x1="12" y1="15" x2="12" y2="22"/><line x1="17" y1="15" x2="17" y2="18"/></g></svg>`,
    'freezing-rain': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 12H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 12z" opacity="0.8"/><g fill="currentColor"><polygon points="7,15 8.5,18 7,21 5.5,18" opacity="0.7"/><polygon points="12,15 13.5,19 12,23 10.5,19" opacity="0.7"/><polygon points="17,15 18.5,17 17,19 15.5,17" opacity="0.7"/></g></svg>`,
    'snow': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 12H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 12z" opacity="0.8"/><g fill="currentColor" opacity="0.8"><circle cx="7" cy="16" r="1.5"/><circle cx="12" cy="18" r="1.5"/><circle cx="17" cy="16" r="1.5"/><circle cx="9.5" cy="21" r="1.5"/><circle cx="14.5" cy="21" r="1.5"/></g></svg>`,
    'showers': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 10H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 10z" opacity="0.8"/><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="6" y1="13" x2="6" y2="16"/><line x1="10" y1="14" x2="10" y2="20"/><line x1="14" y1="13" x2="14" y2="18"/><line x1="18" y1="14" x2="18" y2="17"/></g></svg>`,
    'snow-showers': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 10H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 10z" opacity="0.8"/><g fill="currentColor" opacity="0.8"><circle cx="6" cy="14" r="1.5"/><circle cx="10" cy="17" r="1.5"/><circle cx="14" cy="14" r="1.5"/><circle cx="18" cy="17" r="1.5"/><circle cx="8" cy="21" r="1.5"/><circle cx="12" cy="21" r="1.5"/><circle cx="16" cy="21" r="1.5"/></g></svg>`,
    'thunderstorm': `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 10H6a3 3 0 0 1 0-6h.5a4.5 4.5 0 0 1 8.5 1.84A2.5 2.5 0 0 1 18 10z" opacity="0.8"/><polygon points="13,12 10,18 12,18 11,23 15,16 13,16" fill="#fbbf24"/></svg>`,
    'unknown': `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/><text x="12" y="16" text-anchor="middle" font-size="10">?</text></svg>`
};

const WeatherWidget = {
    name: 'weather',
    version: '1.0.0',
    author: 'built-in',

    configSchema: {
        location: { required: true },
        units: { enum: ['imperial', 'metric'], default: 'imperial' },
        display: { enum: ['current', 'hourly', 'daily', 'full'], default: 'current' },
        hours_to_show: { default: 7 },
        days_to_show: { default: 7 },
        show_humidity: { default: true },
        show_wind: { default: true },
        show_precipitation: { default: true },
        refresh_interval: { default: 1800000 }  // 30 min
    },

    create(container, config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'widget-weather';
        wrapper.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            font-family: inherit;
            color: inherit;
            padding: 1rem;
            box-sizing: border-box;
            overflow: hidden;
        `;

        // Show loading state
        wrapper.innerHTML = '<div style="opacity: 0.5;">Loading weather...</div>';

        // Start fetching weather data
        this._initWeather(wrapper, config);

        return wrapper;
    },

    async _initWeather(wrapper, config) {
        try {
            // Geocode location if needed
            const coords = await this._geocodeLocation(config.location);
            if (!coords) {
                wrapper.innerHTML = `<div style="opacity: 0.5;">Location not found: ${config.location}</div>`;
                return;
            }

            // Fetch weather data
            const weatherData = await this._fetchWeather(coords, config);
            if (!weatherData) {
                wrapper.innerHTML = '<div style="opacity: 0.5;">Failed to load weather</div>';
                return;
            }

            // Render weather based on display mode
            this._renderWeather(wrapper, weatherData, config);

            // Set up auto-refresh
            const intervalId = setInterval(async () => {
                const newData = await this._fetchWeather(coords, config);
                if (newData) {
                    this._renderWeather(wrapper, newData, config);
                }
            }, config.refresh_interval);

            wrapper._weatherIntervalId = intervalId;
            wrapper._weatherCoords = coords;
        } catch (error) {
            console.error('Weather widget error:', error);
            wrapper.innerHTML = `<div style="opacity: 0.5;">Error: ${error.message}</div>`;
        }
    },

    async _geocodeLocation(location) {
        // Check cache first
        const cacheKey = location.toLowerCase().trim();
        if (geocodeCache.has(cacheKey)) {
            return geocodeCache.get(cacheKey);
        }

        try {
            const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(location)}&count=1&language=en&format=json`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.results && data.results.length > 0) {
                const result = {
                    latitude: data.results[0].latitude,
                    longitude: data.results[0].longitude,
                    name: data.results[0].name,
                    country: data.results[0].country,
                    timezone: data.results[0].timezone
                };
                geocodeCache.set(cacheKey, result);
                return result;
            }
            return null;
        } catch (error) {
            console.error('Geocoding error:', error);
            return null;
        }
    },

    async _fetchWeather(coords, config) {
        try {
            const isMetric = config.units === 'metric';
            const tempUnit = isMetric ? 'celsius' : 'fahrenheit';
            const windUnit = isMetric ? 'kmh' : 'mph';
            const precipUnit = isMetric ? 'mm' : 'inch';

            const params = new URLSearchParams({
                latitude: coords.latitude,
                longitude: coords.longitude,
                current: 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,precipitation',
                hourly: 'temperature_2m,weather_code,precipitation_probability',
                daily: 'temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum,precipitation_probability_max',
                temperature_unit: tempUnit,
                wind_speed_unit: windUnit,
                precipitation_unit: precipUnit,
                timezone: coords.timezone || 'auto',
                forecast_days: Math.min(config.days_to_show, 16)
            });

            const url = `https://api.open-meteo.com/v1/forecast?${params}`;
            const response = await fetch(url);
            const data = await response.json();

            return {
                location: coords,
                current: data.current,
                hourly: data.hourly,
                daily: data.daily,
                units: { temp: isMetric ? '°C' : '°F', wind: windUnit, precip: precipUnit }
            };
        } catch (error) {
            console.error('Weather fetch error:', error);
            return null;
        }
    },

    _renderWeather(wrapper, data, config) {
        wrapper.innerHTML = '';

        switch (config.display) {
            case 'hourly':
                this._renderCurrentAndHourly(wrapper, data, config);
                break;
            case 'daily':
                this._renderCurrentAndDaily(wrapper, data, config);
                break;
            case 'full':
                this._renderFull(wrapper, data, config);
                break;
            case 'current':
            default:
                this._renderCurrent(wrapper, data, config);
        }
    },

    _renderCurrent(wrapper, data, config) {
        const current = data.current;
        const weatherInfo = WEATHER_CODES[current.weather_code] || { icon: 'unknown', description: 'Unknown' };

        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            width: 100%;
        `;

        // Location name
        const locationEl = document.createElement('div');
        locationEl.style.cssText = 'font-size: 1.2rem; opacity: 0.7;';
        locationEl.textContent = data.location.name;
        container.appendChild(locationEl);

        // Main temp and icon row
        const mainRow = document.createElement('div');
        mainRow.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
        `;

        const iconEl = document.createElement('div');
        iconEl.style.cssText = 'width: 4rem; height: 4rem;';
        iconEl.innerHTML = WEATHER_ICONS[weatherInfo.icon] || WEATHER_ICONS['unknown'];
        mainRow.appendChild(iconEl);

        const tempEl = document.createElement('div');
        tempEl.style.cssText = 'font-size: 4rem; font-weight: 300; line-height: 1;';
        tempEl.textContent = `${Math.round(current.temperature_2m)}${data.units.temp}`;
        mainRow.appendChild(tempEl);

        container.appendChild(mainRow);

        // Condition description
        const conditionEl = document.createElement('div');
        conditionEl.style.cssText = 'font-size: 1.2rem; opacity: 0.8;';
        conditionEl.textContent = weatherInfo.description;
        container.appendChild(conditionEl);

        // Details row
        const detailsRow = document.createElement('div');
        detailsRow.style.cssText = `
            display: flex;
            gap: 1.5rem;
            margin-top: 0.5rem;
            font-size: 0.9rem;
            opacity: 0.7;
        `;

        if (config.show_humidity) {
            const humidityEl = document.createElement('div');
            humidityEl.textContent = `💧 ${current.relative_humidity_2m}%`;
            detailsRow.appendChild(humidityEl);
        }

        if (config.show_wind) {
            const windEl = document.createElement('div');
            windEl.textContent = `💨 ${Math.round(current.wind_speed_10m)} ${data.units.wind}`;
            detailsRow.appendChild(windEl);
        }

        if (config.show_precipitation && current.precipitation > 0) {
            const precipEl = document.createElement('div');
            precipEl.textContent = `🌧️ ${current.precipitation} ${data.units.precip}`;
            detailsRow.appendChild(precipEl);
        }

        container.appendChild(detailsRow);

        wrapper.appendChild(container);
        this._autoScale(wrapper);
    },

    _renderCurrentAndHourly(wrapper, data, config) {
        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            gap: 1rem;
        `;

        // Current conditions (smaller)
        const currentSection = document.createElement('div');
        currentSection.style.cssText = 'flex: 0 0 auto;';
        this._renderCurrentCompact(currentSection, data, config);
        container.appendChild(currentSection);

        // Hourly forecast
        const hourlySection = document.createElement('div');
        hourlySection.style.cssText = `
            flex: 1;
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            align-items: center;
            justify-content: center;
        `;

        const now = new Date();
        const currentHour = now.getHours();
        let hoursRendered = 0;

        for (let i = 0; i < data.hourly.time.length && hoursRendered < config.hours_to_show; i++) {
            const hourTime = new Date(data.hourly.time[i]);
            if (hourTime <= now) continue;

            const hourEl = this._createHourlyItem(
                hourTime,
                data.hourly.temperature_2m[i],
                data.hourly.weather_code[i],
                data.hourly.precipitation_probability[i],
                data.units,
                config
            );
            hourlySection.appendChild(hourEl);
            hoursRendered++;
        }

        container.appendChild(hourlySection);
        wrapper.appendChild(container);
    },

    _renderCurrentAndDaily(wrapper, data, config) {
        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            gap: 1rem;
        `;

        // Current conditions (smaller)
        const currentSection = document.createElement('div');
        currentSection.style.cssText = 'flex: 0 0 auto;';
        this._renderCurrentCompact(currentSection, data, config);
        container.appendChild(currentSection);

        // Daily forecast
        const dailySection = document.createElement('div');
        dailySection.style.cssText = `
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            overflow-y: auto;
        `;

        for (let i = 0; i < Math.min(data.daily.time.length, config.days_to_show); i++) {
            const dayEl = this._createDailyItem(
                data.daily.time[i],
                data.daily.temperature_2m_max[i],
                data.daily.temperature_2m_min[i],
                data.daily.weather_code[i],
                data.daily.precipitation_probability_max[i],
                data.units,
                config,
                i === 0
            );
            dailySection.appendChild(dayEl);
        }

        container.appendChild(dailySection);
        wrapper.appendChild(container);
    },

    _renderFull(wrapper, data, config) {
        const container = document.createElement('div');
        container.style.cssText = `
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto 1fr;
            width: 100%;
            height: 100%;
            gap: 1rem;
        `;

        // Current conditions (top left)
        const currentSection = document.createElement('div');
        currentSection.style.cssText = 'grid-column: 1 / -1;';
        this._renderCurrentCompact(currentSection, data, config);
        container.appendChild(currentSection);

        // Hourly (bottom left)
        const hourlySection = document.createElement('div');
        hourlySection.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            overflow-y: auto;
        `;

        const now = new Date();
        let hoursRendered = 0;
        for (let i = 0; i < data.hourly.time.length && hoursRendered < config.hours_to_show; i++) {
            const hourTime = new Date(data.hourly.time[i]);
            if (hourTime <= now) continue;

            const hourEl = this._createHourlyItemCompact(
                hourTime,
                data.hourly.temperature_2m[i],
                data.hourly.weather_code[i],
                data.units
            );
            hourlySection.appendChild(hourEl);
            hoursRendered++;
        }
        container.appendChild(hourlySection);

        // Daily (bottom right)
        const dailySection = document.createElement('div');
        dailySection.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            overflow-y: auto;
        `;

        for (let i = 0; i < Math.min(data.daily.time.length, config.days_to_show); i++) {
            const dayEl = this._createDailyItem(
                data.daily.time[i],
                data.daily.temperature_2m_max[i],
                data.daily.temperature_2m_min[i],
                data.daily.weather_code[i],
                data.daily.precipitation_probability_max[i],
                data.units,
                config,
                i === 0
            );
            dailySection.appendChild(dayEl);
        }
        container.appendChild(dailySection);

        wrapper.appendChild(container);
    },

    _renderCurrentCompact(container, data, config) {
        const current = data.current;
        const weatherInfo = WEATHER_CODES[current.weather_code] || { icon: 'unknown', description: 'Unknown' };

        container.innerHTML = '';
        container.style.cssText += `
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
        `;

        // Location
        const locationEl = document.createElement('div');
        locationEl.style.cssText = 'font-size: 1rem; opacity: 0.7;';
        locationEl.textContent = data.location.name;
        container.appendChild(locationEl);

        // Icon
        const iconEl = document.createElement('div');
        iconEl.style.cssText = 'width: 2.5rem; height: 2.5rem;';
        iconEl.innerHTML = WEATHER_ICONS[weatherInfo.icon] || WEATHER_ICONS['unknown'];
        container.appendChild(iconEl);

        // Temp
        const tempEl = document.createElement('div');
        tempEl.style.cssText = 'font-size: 2rem; font-weight: 300;';
        tempEl.textContent = `${Math.round(current.temperature_2m)}${data.units.temp}`;
        container.appendChild(tempEl);

        // Details
        const detailsEl = document.createElement('div');
        detailsEl.style.cssText = 'font-size: 0.8rem; opacity: 0.6;';
        const details = [];
        if (config.show_humidity) details.push(`${current.relative_humidity_2m}%`);
        if (config.show_wind) details.push(`${Math.round(current.wind_speed_10m)} ${data.units.wind}`);
        detailsEl.textContent = details.join(' · ');
        container.appendChild(detailsEl);
    },

    _createHourlyItem(time, temp, weatherCode, precipProb, units, config) {
        const weatherInfo = WEATHER_CODES[weatherCode] || { icon: 'unknown' };

        const item = document.createElement('div');
        item.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.25rem;
            padding: 0.5rem;
            min-width: 3.5rem;
        `;

        const timeEl = document.createElement('div');
        timeEl.style.cssText = 'font-size: 0.8rem; opacity: 0.7;';
        timeEl.textContent = time.toLocaleTimeString([], { hour: 'numeric' });
        item.appendChild(timeEl);

        const iconEl = document.createElement('div');
        iconEl.style.cssText = 'width: 1.5rem; height: 1.5rem;';
        iconEl.innerHTML = WEATHER_ICONS[weatherInfo.icon] || WEATHER_ICONS['unknown'];
        item.appendChild(iconEl);

        const tempEl = document.createElement('div');
        tempEl.style.cssText = 'font-size: 1rem; font-weight: 500;';
        tempEl.textContent = `${Math.round(temp)}°`;
        item.appendChild(tempEl);

        if (config.show_precipitation && precipProb > 20) {
            const precipEl = document.createElement('div');
            precipEl.style.cssText = 'font-size: 0.7rem; opacity: 0.6;';
            precipEl.textContent = `${precipProb}%`;
            item.appendChild(precipEl);
        }

        return item;
    },

    _createHourlyItemCompact(time, temp, weatherCode, units) {
        const weatherInfo = WEATHER_CODES[weatherCode] || { icon: 'unknown' };

        const item = document.createElement('div');
        item.style.cssText = `
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0;
        `;

        const timeEl = document.createElement('div');
        timeEl.style.cssText = 'font-size: 0.8rem; opacity: 0.7; min-width: 2.5rem;';
        timeEl.textContent = time.toLocaleTimeString([], { hour: 'numeric' });
        item.appendChild(timeEl);

        const iconEl = document.createElement('div');
        iconEl.style.cssText = 'width: 1.2rem; height: 1.2rem;';
        iconEl.innerHTML = WEATHER_ICONS[weatherInfo.icon] || WEATHER_ICONS['unknown'];
        item.appendChild(iconEl);

        const tempEl = document.createElement('div');
        tempEl.style.cssText = 'font-size: 0.9rem;';
        tempEl.textContent = `${Math.round(temp)}°`;
        item.appendChild(tempEl);

        return item;
    },

    _createDailyItem(date, maxTemp, minTemp, weatherCode, precipProb, units, config, isToday) {
        const weatherInfo = WEATHER_CODES[weatherCode] || { icon: 'unknown' };
        const dayDate = new Date(date);

        const item = document.createElement('div');
        item.style.cssText = `
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.35rem 0;
            ${isToday ? 'opacity: 1; font-weight: 500;' : 'opacity: 0.85;'}
        `;

        // Day name
        const dayEl = document.createElement('div');
        dayEl.style.cssText = 'font-size: 0.9rem; min-width: 3rem;';
        dayEl.textContent = isToday ? 'Today' : dayDate.toLocaleDateString([], { weekday: 'short' });
        item.appendChild(dayEl);

        // Icon
        const iconEl = document.createElement('div');
        iconEl.style.cssText = 'width: 1.3rem; height: 1.3rem;';
        iconEl.innerHTML = WEATHER_ICONS[weatherInfo.icon] || WEATHER_ICONS['unknown'];
        item.appendChild(iconEl);

        // Precip probability
        if (config.show_precipitation) {
            const precipEl = document.createElement('div');
            precipEl.style.cssText = 'font-size: 0.75rem; opacity: 0.6; min-width: 2rem;';
            precipEl.textContent = precipProb > 10 ? `${precipProb}%` : '';
            item.appendChild(precipEl);
        }

        // High/Low temps
        const tempEl = document.createElement('div');
        tempEl.style.cssText = 'font-size: 0.9rem; margin-left: auto;';
        tempEl.innerHTML = `<span>${Math.round(maxTemp)}°</span> <span style="opacity: 0.5">${Math.round(minTemp)}°</span>`;
        item.appendChild(tempEl);

        return item;
    },

    _autoScale(wrapper) {
        // Simple auto-scale for current view
        requestAnimationFrame(() => {
            const parent = wrapper.closest('.panel-content');
            if (!parent) return;

            const scale = Math.min(
                parent.clientWidth / 300,
                parent.clientHeight / 200
            );

            if (scale > 1) {
                wrapper.style.transform = `scale(${Math.min(scale, 2.5)})`;
            }
        });
    },

    update(element, config) {
        this.destroy(element);
        const parent = element.parentNode;
        const newElement = this.create(parent, config);
        parent.replaceChild(newElement, element);
        return newElement;
    },

    destroy(element) {
        if (element && element._weatherIntervalId) {
            clearInterval(element._weatherIntervalId);
            element._weatherIntervalId = null;
        }
    }
};

// Register the widget
registerWidget('weather', WeatherWidget);

export default WeatherWidget;
