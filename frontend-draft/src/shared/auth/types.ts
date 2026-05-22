export type UserRole = "admin" | "rep";

export type CurrentUser = {
  profileId: string;
  email: string;
  name: string;
  companyName: string;
  role: UserRole;
  signedUpAt: string;
};
