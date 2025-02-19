from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('shop/', views.ShopView.as_view(), name='shop'),
    path('add-to-cart/<slug:slug>/', views.add_to_cart, name='add-to-cart'),
    path('shop-details/<slug:product_slug>/', views.ProductDetailView.as_view(), name='shop-details'),
    path('shopping-cart/', views.CartView.as_view(), name='shopping-cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('blog/', views.BlogView.as_view(), name='blog'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('blog-details/<int:pk>/', views.BlogDetailView.as_view(), name='blog-details'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove-from-cart'),
]
