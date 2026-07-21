export const LICENSE_NAMES_MAP = {
  'SPB': 'Microsoft 365 Empresa Premium',
  'ENTERPRISEPACK': 'Office 365 E3',
  'STANDARDPACK': 'Office 365 E1',
  'TEAMS_EXPLORATORY': 'Microsoft Teams Exploratory',
  'ENTERPRISEPREMIUM': 'Office 365 E5',
  'O365_BUSINESS_PREMIUM': 'Microsoft 365 Empresa Estándar',
  'O365_BUSINESS_ESSENTIALS': 'Microsoft 365 Empresa Básico',
  'POWER_BI_PRO': 'Power BI Pro',
  'POWER_BI_STANDARD': 'Microsoft Fabric (Gratis)',
  'FLOW_FREE': 'Microsoft Power Automate Free',
  'MICROSOFT_BUSINESS_CENTER': 'Microsoft Business Center',
  'CCIBOTS_PRIVPREV_VIRAL': 'Evaluación viral de Copilot Studio',
  'POWERAPPS_VIRAL': 'Microsoft Power Apps Plan 2 Trial',
  'POWERAPPS_DEV': 'Microsoft Power Apps for Developer',
  'Microsoft_Teams_Enterprise_New': 'Microsoft Teams Enterprise',
  'Power_Pages_vTrial_for_Makers': 'Power Pages Trial para Creadores',
  'POWERAPPS_PER_USER': 'Power Apps por usuario',
  'POWERAPPS_PER_APP_NEW': 'Power Apps por aplicación',
  'Teams_Premium_(for_Departments)': 'Teams Premium',
  'WINDOWS_STORE': 'Tienda de Windows',
  'Office_365_E5_(no_Teams)': 'Office 365 E5 (Sin Teams)',
  'STREAM': 'Microsoft Stream'
}

export function getFriendlyLicenseName(skuPartNumber) {
  if (!skuPartNumber) return 'Desconocida';
  return LICENSE_NAMES_MAP[skuPartNumber] || skuPartNumber;
}
