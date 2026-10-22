import { api } from "./api";

const qs = (params) => {
  const s = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  return s ? `?${s}` : "";
};

export const movieService = {
  cities: () => api.get("/cities"),
  movies: (params = {}) => api.get(`/movies${qs(params)}`),
  promotions: () => api.get("/promotions"),
  movie: (id) => api.get(`/movies/${id}`),
  movieReviews: (id, page = 1) => api.get(`/movies/${id}/reviews?page=${page}`),
  myMovieReview: (id) => api.get(`/movies/${id}/reviews/mine`),
  saveMovieReview: (id, body) => api.post(`/movies/${id}/reviews`, body),
  deleteMyMovieReview: (id) => api.delete(`/movies/${id}/reviews/mine`),
  watchableMovies: () => api.get("/movies/watch"),
  cinemas: (city) => api.get(`/cinemas${qs({ city })}`),
  showtimes: (params = {}) => api.get(`/showtimes${qs(params)}`),
  seatMap: (showtimeId) => api.get(`/showtimes/${showtimeId}/seats`),
  foods: () => api.get("/foods"),
};
